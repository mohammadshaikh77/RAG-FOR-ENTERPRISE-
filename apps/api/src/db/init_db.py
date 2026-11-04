import asyncio

from sqlalchemy import text

from apps.api.src.db.session import engine
from apps.api.src.logging import get_logger
from apps.api.src.models.agent_trace import AgentTrace  # noqa: F401
from apps.api.src.models.base import Base
from apps.api.src.models.chunk import DocumentChunk  # noqa: F401
from apps.api.src.models.document import Document  # noqa: F401
from apps.api.src.models.drug_metadata import DrugMetadata  # noqa: F401
from apps.api.src.models.organization import Organization  # noqa: F401
from apps.api.src.models.user import User  # noqa: F401

logger = get_logger("cite.db.init")


async def init_db() -> None:
    """Initializes the database schema and pgvector extension."""
    logger.info("Initializing database schema...")
    async with engine.begin() as conn:
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database schema initialized successfully.")


if __name__ == "__main__":
    asyncio.run(init_db())
