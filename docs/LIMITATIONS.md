# Cite Platform — Known Limitations & System Boundaries

This document records architectural boundaries, current operational constraints, and honest trade-offs across all phases of the Cite platform.

---

## 1. Resource & Hardware Boundaries
- **Local Embedding Execution**: The default embedding model (`sentence-transformers/all-MiniLM-L6-v2`) runs on the host CPU. While CPU inference takes only ~15–30 ms per chunk, large batch ingests (>500 documents) will take several minutes unless chunking/embedding is distributed across multiple worker threads.
- **Reranker Memory Consumption**: Cross-encoders (`ms-marco-TinyBERT-L-2-v2`) provide superior re-ranking accuracy over raw vector search, but add ~80–120 MB RAM overhead. To ensure 8 GB developer laptops run without swapping, reranking is disabled by default via `ENABLE_RERANKER=false` and must be explicitly enabled for high-accuracy evaluation runs.
- **Local LLM Demands**: Running 7B/8B models locally via Ollama requires 5–6 GB of unified RAM. For constrained machines, cloud free-tier providers (Groq, Gemini) or Mock modes are recommended.

## 2. API Quotas & Free Tier Caps
- **Groq Free Tier**: Hard rate limit of 30 RPM (Requests Per Minute) and 14,400 RPD (Requests Per Day) on `llama-3.1-8b-instant`.
- **Gemini Free Tier**: Capped at 15 RPM and 1,500 RPD on `gemini-1.5-flash`.
- **Mitigation & Boundary**: The platform implements token-bucket throttling and automatic failover. However, sustained parallel automated evaluation runs can temporarily exhaust free quotas if run without pacing.

## 3. Ingestion & Document Parsing
- **Scanned Document OCR**: Current parsers process digital text, structured PDFs, and HTML. Optical Character Recognition (OCR) for scanned image-only PDFs is not included in the default zero-dependency pipeline to avoid heavy system dependencies (like Tesseract binaries).
- **Multilingual Full-Text Stemming**: PostgreSQL full-text search currently uses the `'english'` dictionary. Non-English drug labels or international filings will index without language-specific stemming unless dictionary configurations are parameterized.

## 4. Multi-Tenancy Scoping
- **Session-Based Isolation**: Tenant isolation is enforced via repository query filters and Postgres Row-Level Security (RLS). Superuser / direct database connections bypass RLS; application connections must always run under non-superuser credentials with `app.current_org_id` bound.

## 5. Retrieval & RRF Calibration
- **RRF Score Interpretation**: Reciprocal Rank Fusion scores reflect relative combined ordering ($RRF\_score \in [0, 0.033]$ for $k=60$) rather than absolute cosine similarities. Downstream confidence thresholds must calibrate against RRF ranges rather than expecting normalized $0.0 - 1.0$ dot products.

## 6. Agent Tool-Calling Bounds & Latency
- **Sequential Tool Execution**: In multi-step reasoning runs, each LLM call and subsequent tool execution adds latency (approx. 300–800 ms per step on Groq, 1–2 s on Gemini). For a 3-step query, total latency ranges from 1.5 s to 5 s.
- **Max Step Truncation**: When `max_steps` (default 5) is reached before complete synthesis, the agent concludes with available partial evidence or explicit refusal rather than recursing indefinitely.

## 7. Frontend & Browser Capabilities
- **Plain JavaScript Architecture**: The frontend intentionally uses modern JavaScript (ES6+ / JSX) with JSDoc rather than TypeScript to keep build times ultra-fast (<2s) and eliminate complex compilation toolchains. Type checking relies on FastAPI/Pydantic schemas on the server side and JSDoc contracts on the client.
- **Client-Side Span Highlighting**: Citations highlight supporting evidence spans using case-insensitive substring matching within the retrieved chunk text. If an LLM slightly adapts punctuation in the quote rather than verbatim copying, the UI highlights the excerpt in a distinct callout card above the chunk text rather than failing silently.
- **Port 3001 Default**: Vite dev server and Docker web container bind to port 3001 by default to prevent port conflicts on developer machines where 3000 is occupied.



