import uuid

import pytest
from httpx import ASGITransport, AsyncClient

from apps.api.src.db.session import async_session_maker
from apps.api.src.main import app
from packages.rag.src.rag.embeddings import MockEmbedder
from packages.rag.src.rag.reranker import MockReranker
from packages.rag.src.rag.search import HybridRetriever, RetrievalMode

DEMO_ORG_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")


@pytest.mark.asyncio
async def test_hybrid_search_end_to_end() -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        payload = {
            "query": "boxed warning cardiovascular",
            "org_id": str(DEMO_ORG_ID),
            "mode": "hybrid",
            "top_k": 3,
        }
        resp = await client.post("/retrieval/search", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        assert data["mode"] == "hybrid"
        assert len(data["results"]) > 0

        # Verify score and citation metadata
        first_chunk = data["results"][0]
        assert "document_title" in first_chunk
        assert "section_title" in first_chunk
        assert "section_path" in first_chunk
        assert first_chunk["score"] > 0
        assert first_chunk["rank"] == 1


@pytest.mark.asyncio
async def test_retrieval_ablations() -> None:
    """Verifies that all 4 ablation switches execute cleanly."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        modes = ["vector", "keyword", "hybrid", "hybrid_rerank"]
        for mode in modes:
            payload = {
                "query": "hypertension dosage",
                "org_id": str(DEMO_ORG_ID),
                "mode": mode,
                "top_k": 2,
            }
            resp = await client.post("/retrieval/search", json=payload)
            assert resp.status_code == 200
            data = resp.json()
            assert data["mode"] == mode
            assert len(data["results"]) <= 2


@pytest.mark.asyncio
async def test_retrieval_section_filter() -> None:
    """Verifies filtering by section name."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        payload = {
            "query": "warning",
            "org_id": str(DEMO_ORG_ID),
            "mode": "keyword",
            "section": "Boxed Warning",
            "top_k": 3,
        }
        resp = await client.post("/retrieval/search", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        for item in data["results"]:
            assert "Boxed Warning" in (item["section_title"] or "")


@pytest.mark.asyncio
async def test_retriever_unit_with_mock_embedder() -> None:
    """Unit test for HybridRetriever with mock embedder."""
    mock_retriever = HybridRetriever(
        embedder=MockEmbedder(),
        reranker=MockReranker(),
    )
    async with async_session_maker() as session:
        results = await mock_retriever.search(
            session=session,
            query="infection antibacterial",
            org_id=DEMO_ORG_ID,
            mode=RetrievalMode.HYBRID,
            top_k=2,
        )
        assert len(results) > 0
        assert results[0].score > 0
