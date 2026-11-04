import uuid

import pytest
from sqlalchemy import select

from apps.api.src.db.session import async_session_maker
from apps.api.src.models.document import Document
from apps.api.src.models.organization import Organization
from packages.rag.src.rag.embeddings import MockEmbedder
from packages.rag.src.rag.ingestion import IngestionService


@pytest.mark.asyncio
async def test_ingestion_idempotency_unit() -> None:
    test_org_id = uuid.uuid4()
    service = IngestionService(embedder=MockEmbedder())

    async with async_session_maker() as session:
        # Create test organization
        org = Organization(id=test_org_id, name="Idempotency Org", slug=f"idemp-{test_org_id}")
        session.add(org)
        await session.commit()

        content = "# Test Drug\n\nThis is a unique drug label for idempotency testing."

        # First ingestion
        doc1, is_dup1 = await service.ingest(
            session=session,
            org_id=test_org_id,
            raw_content=content,
            file_type="text/markdown",
            title="Idempotency Drug",
        )
        assert is_dup1 is False
        assert doc1.chunk_count > 0

        # Second ingestion with identical content
        doc2, is_dup2 = await service.ingest(
            session=session,
            org_id=test_org_id,
            raw_content=content,
            file_type="text/markdown",
            title="Idempotency Drug",
        )
        assert is_dup2 is True
        assert doc1.id == doc2.id

        # Verify only 1 document exists in database for this org
        stmt = select(Document).where(Document.org_id == test_org_id)
        res = await session.execute(stmt)
        docs = res.scalars().all()
        assert len(docs) == 1
