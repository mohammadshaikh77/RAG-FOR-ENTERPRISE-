import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.src.db.session import get_db
from apps.api.src.models.organization import Organization
from packages.rag.src.rag.search import HybridRetriever, RetrievalMode, RetrievalResult

router = APIRouter(prefix="/retrieval", tags=["Retrieval"])
retriever = HybridRetriever()


class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1, description="Search query string")
    org_id: uuid.UUID = Field(..., description="Tenant organization ID")
    mode: RetrievalMode = Field(
        default=RetrievalMode.HYBRID,
        description="Ablation mode: vector, keyword, hybrid, hybrid_rerank",
    )
    top_k: int = Field(default=5, ge=1, le=50)
    document_id: uuid.UUID | None = Field(default=None, description="Optional document filter")
    section: str | None = Field(default=None, description="Optional section title filter")


class SearchResultItem(BaseModel):
    chunk_id: uuid.UUID
    document_id: uuid.UUID
    document_title: str
    content: str
    section_title: str | None = None
    section_path: str | None = None
    page_number: int | None = None
    score: float
    rank: int
    vector_score: float | None = None
    keyword_score: float | None = None
    rerank_score: float | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class SearchResponse(BaseModel):
    query: str
    mode: str
    total_results: int
    results: list[SearchResultItem]


@router.post("/search", response_model=SearchResponse)
async def search_chunks(
    payload: SearchRequest,
    db: AsyncSession = Depends(get_db),
) -> SearchResponse:
    """Executes hybrid vector/keyword search with RRF and optional reranking."""
    # Tenant verification
    org = await db.get(Organization, payload.org_id)
    if not org:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Organization {payload.org_id} not found",
        )

    results: list[RetrievalResult] = await retriever.search(
        session=db,
        query=payload.query,
        org_id=payload.org_id,
        mode=payload.mode,
        top_k=payload.top_k,
        document_id=payload.document_id,
        section=payload.section,
    )

    items = [
        SearchResultItem(
            chunk_id=r.chunk_id,
            document_id=r.document_id,
            document_title=r.document_title,
            content=r.content,
            section_title=r.section_title,
            section_path=r.section_path,
            page_number=r.page_number,
            score=r.score,
            rank=r.rank,
            vector_score=r.vector_score,
            keyword_score=r.keyword_score,
            rerank_score=r.rerank_score,
            metadata=r.metadata,
        )
        for r in results
    ]

    return SearchResponse(
        query=payload.query,
        mode=payload.mode.value,
        total_results=len(items),
        results=items,
    )
