import enum
import uuid
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.src.logging import get_logger
from apps.api.src.models.chunk import DocumentChunk
from apps.api.src.models.document import Document
from packages.rag.src.rag.embeddings import Embedder, get_embedder
from packages.rag.src.rag.reranker import Reranker, get_reranker

logger = get_logger("cite.rag.search")


class RetrievalMode(enum.StrEnum):
    VECTOR = "vector"
    KEYWORD = "keyword"
    HYBRID = "hybrid"
    HYBRID_RERANK = "hybrid_rerank"


@dataclass
class RetrievalResult:
    """Scored chunk citation returned by retrieval engine."""

    chunk_id: uuid.UUID
    document_id: uuid.UUID
    document_title: str
    org_id: uuid.UUID
    content: str
    section_title: str | None
    section_path: str | None
    page_number: int | None
    score: float
    rank: int = 1
    vector_score: float | None = None
    keyword_score: float | None = None
    rerank_score: float | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


class HybridRetriever:
    """Hybrid retrieval engine combining pgvector and Postgres FTS via RRF."""

    def __init__(
        self,
        embedder: Embedder | None = None,
        reranker: Reranker | None = None,
    ) -> None:
        self.embedder = embedder or get_embedder()
        self.reranker = reranker or get_reranker()

    async def _search_vector(
        self,
        session: AsyncSession,
        org_id: uuid.UUID,
        query_vector: list[float],
        k: int,
        document_id: uuid.UUID | None = None,
        section: str | None = None,
    ) -> list[tuple[DocumentChunk, str, float]]:
        """Dense vector search using pgvector cosine distance: 1 - (embedding <=> query_vec)."""
        cosine_distance = DocumentChunk.embedding.cosine_distance(query_vector)
        similarity = (1 - cosine_distance).label("vector_sim")

        stmt = (
            select(DocumentChunk, Document.title, similarity)
            .join(Document, DocumentChunk.document_id == Document.id)
            .where(
                DocumentChunk.org_id == org_id,
                DocumentChunk.embedding.isnot(None),
            )
        )

        if document_id:
            stmt = stmt.where(DocumentChunk.document_id == document_id)
        if section:
            stmt = stmt.where(DocumentChunk.section_title.ilike(f"%{section}%"))

        stmt = stmt.order_by(cosine_distance).limit(k)
        result = await session.execute(stmt)
        return [(row[0], row[1], float(row[2])) for row in result.all()]

    async def _search_keyword(
        self,
        session: AsyncSession,
        org_id: uuid.UUID,
        query: str,
        k: int,
        document_id: uuid.UUID | None = None,
        section: str | None = None,
    ) -> list[tuple[DocumentChunk, str, float]]:
        """Sparse keyword search using Postgres full-text search with English stemming."""
        # Clean query for websearch syntax
        clean_query = query.strip()
        ts_query = func.websearch_to_tsquery("english", clean_query)
        ts_rank = func.ts_rank_cd(DocumentChunk.tsv_content, ts_query).label("rank_score")

        stmt = (
            select(DocumentChunk, Document.title, ts_rank)
            .join(Document, DocumentChunk.document_id == Document.id)
            .where(
                DocumentChunk.org_id == org_id,
                DocumentChunk.tsv_content.bool_op("@@")(ts_query),
            )
        )

        if document_id:
            stmt = stmt.where(DocumentChunk.document_id == document_id)
        if section:
            stmt = stmt.where(DocumentChunk.section_title.ilike(f"%{section}%"))

        stmt = stmt.order_by(desc(ts_rank)).limit(k)
        result = await session.execute(stmt)
        return [(row[0], row[1], float(row[2])) for row in result.all()]

    async def search(
        self,
        session: AsyncSession,
        query: str,
        org_id: uuid.UUID,
        mode: RetrievalMode = RetrievalMode.HYBRID,
        top_k: int = 5,
        candidate_k: int = 20,
        document_id: uuid.UUID | None = None,
        section: str | None = None,
        rrf_k: int = 60,
    ) -> list[RetrievalResult]:
        """
        Executes search under the specified ablation mode:
        - vector: dense semantic search only
        - keyword: full-text search only
        - hybrid: RRF combination of vector and keyword
        - hybrid_rerank: hybrid search + cross-encoder reranking
        """
        logger.info(
            "Executing retrieval",
            query=query,
            org_id=str(org_id),
            mode=mode.value,
            top_k=top_k,
        )

        # 1. Vector Only Mode
        if mode == RetrievalMode.VECTOR:
            q_vec = self.embedder.embed_query(query)
            vec_rows = await self._search_vector(
                session, org_id, q_vec, k=top_k, document_id=document_id, section=section
            )
            return [
                RetrievalResult(
                    chunk_id=chunk.id,
                    document_id=chunk.document_id,
                    document_title=doc_title,
                    org_id=chunk.org_id,
                    content=chunk.content,
                    section_title=chunk.section_title,
                    section_path=chunk.section_path,
                    page_number=chunk.page_number,
                    score=round(sim, 4),
                    rank=idx + 1,
                    vector_score=round(sim, 4),
                    metadata=chunk.chunk_metadata,
                )
                for idx, (chunk, doc_title, sim) in enumerate(vec_rows)
            ]

        # 2. Keyword Only Mode
        if mode == RetrievalMode.KEYWORD:
            kw_rows = await self._search_keyword(
                session, org_id, query, k=top_k, document_id=document_id, section=section
            )
            return [
                RetrievalResult(
                    chunk_id=chunk.id,
                    document_id=chunk.document_id,
                    document_title=doc_title,
                    org_id=chunk.org_id,
                    content=chunk.content,
                    section_title=chunk.section_title,
                    section_path=chunk.section_path,
                    page_number=chunk.page_number,
                    score=round(rank_score, 4),
                    rank=idx + 1,
                    keyword_score=round(rank_score, 4),
                    metadata=chunk.chunk_metadata,
                )
                for idx, (chunk, doc_title, rank_score) in enumerate(kw_rows)
            ]

        # 3. Hybrid / Hybrid+Rerank Mode (RRF Fusion)
        q_vec = self.embedder.embed_query(query)
        vec_candidates = await self._search_vector(
            session, org_id, q_vec, k=candidate_k, document_id=document_id, section=section
        )
        kw_candidates = await self._search_keyword(
            session, org_id, query, k=candidate_k, document_id=document_id, section=section
        )

        # Reciprocal Rank Fusion
        chunk_map: dict[uuid.UUID, tuple[DocumentChunk, str]] = {}
        vector_scores: dict[uuid.UUID, float] = {}
        keyword_scores: dict[uuid.UUID, float] = {}
        rrf_scores: dict[uuid.UUID, float] = {}

        for rank_idx, (chunk, doc_title, sim) in enumerate(vec_candidates):
            cid = chunk.id
            chunk_map[cid] = (chunk, doc_title)
            vector_scores[cid] = sim
            rrf_scores[cid] = rrf_scores.get(cid, 0.0) + (1.0 / (rrf_k + rank_idx + 1))

        for rank_idx, (chunk, doc_title, rank_score) in enumerate(kw_candidates):
            cid = chunk.id
            chunk_map[cid] = (chunk, doc_title)
            keyword_scores[cid] = rank_score
            rrf_scores[cid] = rrf_scores.get(cid, 0.0) + (1.0 / (rrf_k + rank_idx + 1))

        # Sort by RRF score
        sorted_cids = sorted(rrf_scores.keys(), key=lambda x: rrf_scores[x], reverse=True)
        top_candidates = sorted_cids[
            : (candidate_k if mode == RetrievalMode.HYBRID_RERANK else top_k)
        ]

        # 4. Optional Cross-Encoder Reranking
        if mode == RetrievalMode.HYBRID_RERANK and top_candidates:
            candidate_texts = [chunk_map[cid][0].content for cid in top_candidates]
            rerank_scores = self.reranker.rerank(query, candidate_texts)
            paired = list(zip(top_candidates, rerank_scores, strict=False))
            # Sort descending by cross-encoder score
            paired.sort(key=lambda x: x[1], reverse=True)
            final_cids = [p[0] for p in paired[:top_k]]
            rerank_score_map = dict(paired)
        else:
            final_cids = top_candidates[:top_k]
            rerank_score_map = {}

        results: list[RetrievalResult] = []
        for rank_idx, cid in enumerate(final_cids):
            chunk, doc_title = chunk_map[cid]
            final_score = rerank_score_map.get(cid, rrf_scores.get(cid, 0.0))
            results.append(
                RetrievalResult(
                    chunk_id=chunk.id,
                    document_id=chunk.document_id,
                    document_title=doc_title,
                    org_id=chunk.org_id,
                    content=chunk.content,
                    section_title=chunk.section_title,
                    section_path=chunk.section_path,
                    page_number=chunk.page_number,
                    score=round(final_score, 4),
                    rank=rank_idx + 1,
                    vector_score=round(vector_scores.get(cid, 0.0), 4)
                    if cid in vector_scores
                    else None,
                    keyword_score=round(keyword_scores.get(cid, 0.0), 4)
                    if cid in keyword_scores
                    else None,
                    rerank_score=round(rerank_score_map.get(cid, 0.0), 4)
                    if cid in rerank_score_map
                    else None,
                    metadata=chunk.chunk_metadata,
                )
            )

        return results
