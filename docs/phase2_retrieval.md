# Phase 2 Documentation: Hybrid Retrieval & Ranking Engine

## What Was Built
1. **Hybrid Retrieval Engine (`packages/rag/src/rag/search.py`)**:
   - Dense vector retrieval using pgvector cosine distance: `1 - (document_chunks.embedding <=> query_vec)`.
   - Sparse full-text search using PostgreSQL English dictionary stemming and `ts_rank_cd`.
   - Rank fusion using Reciprocal Rank Fusion (RRF) with constant $k=60$.
   - Cross-encoder reranking integration (`packages/rag/src/rag/reranker.py`).
2. **Ablation Toggles**:
   - `POST /retrieval/search` supports parameter `mode`:
     - `vector`: Pure dense semantic retrieval.
     - `keyword`: Pure PostgreSQL full-text search.
     - `hybrid`: Dense + Sparse combined via RRF.
     - `hybrid_rerank`: Hybrid search with Cross-Encoder reranking.
   - Per-request filters: `document_id`, `section`, `top_k`.
3. **Citation & Score Metadata**:
   - Every returned chunk carries:
     - `chunk_id` and `document_id`
     - `document_title`
     - `section_title` (e.g. *Boxed Warning*)
     - `section_path` (e.g. *Naproxen (NAPROXEN) > Boxed Warning*)
     - `page_number`
     - `score`, `rank`, `vector_score`, `keyword_score`, `rerank_score`
     - Full chunk text content for grounded citations.

## Acceptance Checks Passed
- Retrieval API returns accurate scored chunks on real drug queries (e.g. *"What is the boxed warning for naproxen?"* correctly retrieves the Boxed Warning chunk as rank 1/2).
- Unit and integration tests verify all 4 ablation switches, section filtering, and mock embedding paths.
