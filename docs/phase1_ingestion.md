# Phase 1 Documentation: Ingestion Pipeline & Demo Dataset

## What Was Built
1. **Multi-Format Parsers (`packages/rag/src/rag/parsers/`)**:
   - `TextParser`: Splits plain text and Markdown on headings (`#` through `####`), preserving hierarchical section breadcrumb paths (e.g. `Drug > Indications`).
   - `HTMLParser`: Parses HTML with BeautifulSoup, strips scripts/styles, and extracts hierarchical section trees.
   - `PDFParser`: Page-aware PDF text extraction with PyPDF, tracking `page_number` and metadata.
   - `FDALabelParser`: Specialized clinical parser extracting structured sections from openFDA records (*Boxed Warning*, *Indications and Usage*, *Contraindications*, *Dosage and Administration*, *Warnings and Precautions*, *Adverse Reactions*, *Drug Interactions*, *Clinical Pharmacology*).
2. **Structure-Aware Chunker (`packages/rag/src/rag/chunker.py`)**:
   - Respects section boundaries, headings, and page context.
   - Splits oversized sections on paragraph and sentence boundaries with configurable token limits and overlap.
3. **Embeddings & Persistence**:
   - Local `sentence-transformers/all-MiniLM-L6-v2` embedding generation with SHA256 in-memory caching.
   - Transactional PostgreSQL persistence into `documents` and `document_chunks` with `Vector(384)` and generated `tsvector`.
4. **Idempotency & Deduplication**:
   - Computes SHA256 file hash per organization.
   - Re-uploading an existing completed document returns existing record immediately with `is_duplicate=True` without duplicate database writes.
5. **Real Demo Data (`scripts/fetch_demo_data.py` & `make demo-data`)**:
   - Fetches official US FDA drug labels across 4 core drug classes (Cardiovascular, NSAIDs, Antibiotics, Oncology).
   - Generates verifiable `data/demo_labels/manifest.json`.

## Acceptance Checks Passed
- `make demo-data` runs end-to-end and successfully ingests real FDA drug labels.
- Re-running the script verifies idempotency (`duplicates_skipped=42, new_ingested=0`).
- Automated tests cover chunk boundary splits, parser edge cases, and idempotency guarantees.
