# ADR 0001: Core Architecture, Database, Queue, and Embedding Stack

## Status
Accepted

## Context
Project "Cite" requires an enterprise-style, multi-tenant document intelligence platform with grounded citations and an automated evaluation harness. The system must operate under strict constraints:
1. Zero software/API licensing cost.
2. Capable of running smoothly on developer laptops with 8–16 GB RAM.
3. Fast setup with one-command execution (`make up`).
4. Measurable quality with reproducible evaluation.

## Decisions

### 1. Unified Database: PostgreSQL 16 with `pgvector`
- **Choice**: PostgreSQL 16 + `pgvector` extension.
- **Alternatives Considered**: Separate vector database (Qdrant, Chroma, Pinecone) + relational database.
- **Why**: Maintaining two distinct databases introduces dual-write consistency issues, network latency, and memory bloat on dev machines. PostgreSQL provides ACID guarantees, relational tenant schemas, HNSW/IVFFlat vector indexing, and native English full-text search (`tsvector` + GIN) in a single ~100MB container.

### 2. Task Queue: ARQ (Async Redis Queue)
- **Choice**: `arq` backed by Redis 7.
- **Alternatives Considered**: Celery, RQ.
- **Why**: Celery is heavy (~100MB+ per worker process) and complex to configure. `arq` is lightweight (<30MB RAM), native Python `asyncio`, and integrates directly with FastAPI's event loop and async database sessions.

### 3. Embeddings: Local `sentence-transformers`
- **Choice**: `all-MiniLM-L6-v2` (384 dimensions).
- **Alternatives Considered**: Remote OpenAI/Gemini embedding APIs.
- **Why**: Local CPU inference ensures batch document ingestion does not consume external API quotas or incur costs. `all-MiniLM-L6-v2` takes ~80MB RAM and runs in ~15ms on CPU.

### 4. Multi-Tier LLM Gateway with Automatic Failover
- **Choice**: Abstracted LLM protocol (`generate`, `generate_with_tools`) with priority order: Groq (`llama-3.1-8b-instant`) -> Gemini (`gemini-1.5-flash`) -> Mock / Ollama.
- **Why**: Free-tier APIs have strict rate limits (Groq: 30 RPM, Gemini: 15 RPM). Automatic exponential backoff, rate limiting, and fallback ensure smooth demos without hitting HTTP 429 roadblocks.

## Consequences
- Single container manages both document metadata and semantic vectors.
- Low memory consumption (<600 MB total stack) leaves ample room for developer OS processes.
