import asyncio
import json
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx
from sqlalchemy import select

from apps.api.src.db.session import async_session_maker
from apps.api.src.logging import get_logger, setup_logging
from apps.api.src.models.organization import Organization
from packages.rag.src.rag.ingestion import IngestionService

setup_logging(log_level="INFO", environment="development")
logger = get_logger("cite.scripts.demo_data")

DEMO_DATA_DIR = Path("data/demo_labels")
MANIFEST_PATH = DEMO_DATA_DIR / "manifest.json"

DRUG_QUERIES = [
    # Cardiovascular
    {"query": "openfda.generic_name:metoprolol", "class": "Beta Blocker"},
    {"query": "openfda.generic_name:lisinopril", "class": "ACE Inhibitor"},
    {"query": "openfda.generic_name:atorvastatin", "class": "HMG-CoA Reductase Inhibitor (Statin)"},
    {"query": "openfda.generic_name:amlodipine", "class": "Calcium Channel Blocker"},
    # Analgesic & Anti-Inflammatory
    {"query": "openfda.generic_name:naproxen", "class": "NSAID"},
    {"query": "openfda.generic_name:ibuprofen", "class": "NSAID"},
    {"query": "openfda.generic_name:celecoxib", "class": "COX-2 Inhibitor NSAID"},
    # Anti-Infective
    {"query": "openfda.generic_name:amoxicillin", "class": "Penicillin Antibacterial"},
    {"query": "openfda.generic_name:ciprofloxacin", "class": "Fluoroquinolone Antibacterial"},
    {"query": "openfda.generic_name:azithromycin", "class": "Macrolide Antibacterial"},
    # Oncology & Immunotherapy
    {"query": "openfda.generic_name:imatinib", "class": "Tyrosine Kinase Inhibitor"},
    {"query": "openfda.generic_name:pembrolizumab", "class": "PD-1 Blocking Antibody"},
    # Metabolic & Endocrine
    {"query": "openfda.generic_name:metformin", "class": "Biguanide Antidiabetic"},
    {"query": "openfda.generic_name:levothyroxine", "class": "Thyroid Hormone"},
    {"query": "openfda.generic_name:semaglutide", "class": "GLP-1 Receptor Agonist"},
]


async def fetch_openfda_labels(limit_per_query: int = 5) -> list[dict[str, Any]]:
    """Fetches real public drug labels from openFDA API."""
    DEMO_DATA_DIR.mkdir(parents=True, exist_ok=True)
    downloaded_records: list[dict[str, Any]] = []
    manifest_entries: list[dict[str, Any]] = []

    headers = {"User-Agent": "Cite-Enterprise-RAG/0.1.0"}

    async with httpx.AsyncClient(timeout=15.0, headers=headers) as client:
        for item in DRUG_QUERIES:
            query = item["query"]
            drug_class = item["class"]
            url = f"https://api.fda.gov/drug/label.json?search={query}&limit={limit_per_query}"

            try:
                logger.info("Fetching drug labels from openFDA", query=query, class_name=drug_class)
                resp = await client.get(url)
                if resp.status_code == 200:
                    data = resp.json()
                    results = data.get("results", [])
                    for idx, record in enumerate(results):
                        openfda = record.get("openfda", {})
                        brand = (openfda.get("brand_name") or ["Unknown Brand"])[0]
                        generic = (openfda.get("generic_name") or [query.split(":")[-1]])[0]
                        fda_id = record.get("id", f"{generic}_{idx}")

                        clean_filename = f"{generic.lower().replace(' ', '_')}_{idx}.json"
                        file_path = DEMO_DATA_DIR / clean_filename

                        # Save individual label file
                        with open(file_path, "w", encoding="utf-8") as f:
                            json.dump(record, f, indent=2)

                        manifest_entry = {
                            "fda_id": fda_id,
                            "brand_name": brand,
                            "generic_name": generic,
                            "drug_class": drug_class,
                            "boxed_warning_present": bool(record.get("boxed_warning")),
                            "source_url": url,
                            "file_name": clean_filename,
                            "retrieved_at": datetime.now(UTC).isoformat(),
                        }
                        manifest_entries.append(manifest_entry)
                        downloaded_records.append(record)
                else:
                    logger.warning(
                        "openFDA query returned non-200", status=resp.status_code, query=query
                    )
            except Exception as e:
                logger.warning(
                    "Failed fetching from openFDA, continuing...", error=str(e), query=query
                )

    # Save manifest
    manifest_data = {
        "source": "US Food & Drug Administration (openFDA API)",
        "endpoint": "https://api.fda.gov/drug/label.json",
        "retrieved_at": datetime.now(UTC).isoformat(),
        "total_documents": len(manifest_entries),
        "documents": manifest_entries,
    }
    with open(MANIFEST_PATH, "w", encoding="utf-8") as f:
        json.dump(manifest_data, f, indent=2)

    logger.info(
        "Demo labels downloaded", total=len(downloaded_records), manifest=str(MANIFEST_PATH)
    )
    return downloaded_records


async def ingest_demo_data(records: list[dict[str, Any]]) -> None:
    """Ingests downloaded FDA labels into PostgreSQL under the demo tenant."""
    logger.info("Ingesting demo drug labels into database...")
    ingestion_service = IngestionService()

    async with async_session_maker() as session:
        # Get or create demo organization
        stmt = select(Organization).where(Organization.slug == "demo-pharma")
        result = await session.execute(stmt)
        org = result.scalar_one_or_none()

        if not org:
            org = Organization(
                id=uuid.UUID("00000000-0000-0000-0000-000000000001"),
                name="Demo Pharma Therapeutics",
                slug="demo-pharma",
            )
            session.add(org)
            await session.commit()
            await session.refresh(org)

        ingested_count = 0
        duplicate_count = 0

        for record in records:
            openfda = record.get("openfda", {})
            brand = (openfda.get("brand_name") or ["Unknown"])[0]
            generic = (openfda.get("generic_name") or [brand])[0]
            title = f"{brand} ({generic})"

            doc, is_dup = await ingestion_service.ingest(
                session=session,
                org_id=org.id,
                raw_content=record,
                file_type="application/json+fda_label",
                title=title,
                source_url="https://api.fda.gov/drug/label.json",
                extra_metadata={"imported_via": "make demo-data"},
            )
            if is_dup:
                duplicate_count += 1
            else:
                ingested_count += 1

        logger.info(
            "Demo data ingestion completed",
            org_id=str(org.id),
            new_ingested=ingested_count,
            duplicates_skipped=duplicate_count,
        )


async def main() -> None:
    records = await fetch_openfda_labels(limit_per_query=3)
    if records:
        await ingest_demo_data(records)


if __name__ == "__main__":
    asyncio.run(main())
