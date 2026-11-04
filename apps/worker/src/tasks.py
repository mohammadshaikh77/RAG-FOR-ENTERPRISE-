from typing import Any

from apps.api.src.logging import get_logger

logger = get_logger("cite.worker.tasks")


async def healthcheck_task(ctx: dict[str, Any]) -> str:
    """Simple ping-pong task to verify worker responsiveness."""
    logger.info("Executing worker healthcheck task")
    return "pong"


async def ingest_document_task(
    ctx: dict[str, Any], document_id: str, org_id: str
) -> dict[str, Any]:
    """Placeholder task for document parsing, chunking, and embedding."""
    logger.info("Starting document ingestion task", document_id=document_id, org_id=org_id)
    # Full implementation arrives in Phase 1
    return {"document_id": document_id, "status": "pending_implementation"}
