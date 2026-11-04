"""Tool for comparing clinical sections between two documents."""

import uuid
from typing import Any

import structlog
from sqlalchemy import select

from agent.tools.base import BaseTool, ToolResult
from apps.api.src.models.chunk import DocumentChunk
from apps.api.src.models.document import Document

logger = structlog.get_logger(__name__)


class CompareDocumentsTool(BaseTool):
    """Retrieves and aligns corresponding clinical sections from two documents for side-by-side comparison."""

    name = "compare_documents"
    description = (
        "Compare two documents side-by-side on a specific clinical topic or section "
        "(e.g., compare 'Boxed Warning' or 'Contraindications' between Metoprolol and Lisinopril)."
    )
    parameters = {
        "type": "object",
        "properties": {
            "doc_a_id": {
                "type": "string",
                "description": "UUID of the first document",
            },
            "doc_b_id": {
                "type": "string",
                "description": "UUID of the second document",
            },
            "topic": {
                "type": "string",
                "description": "The clinical topic or section to compare (e.g., 'Boxed Warning', 'Contraindications', 'Adverse Reactions')",
            },
        },
        "required": ["doc_a_id", "doc_b_id", "topic"],
    }

    def __init__(self, session_factory: Any) -> None:
        self.session_factory = session_factory

    async def execute(self, org_id: uuid.UUID, **kwargs: Any) -> ToolResult:
        doc_a_str = kwargs.get("doc_a_id")
        doc_b_str = kwargs.get("doc_b_id")
        topic = kwargs.get("topic", "").strip()

        if not doc_a_str or not doc_b_str or not topic:
            return ToolResult(
                tool_name=self.name,
                success=False,
                data=None,
                error="doc_a_id, doc_b_id, and topic are required",
            )

        try:
            uuid_a = uuid.UUID(doc_a_str)
            uuid_b = uuid.UUID(doc_b_str)
        except ValueError as ve:
            return ToolResult(
                tool_name=self.name, success=False, data=None, error=f"Invalid UUID: {ve}"
            )

        async with self.session_factory() as session:
            try:
                # Retrieve document A info and chunks
                doc_a = (
                    await session.execute(
                        select(Document).where(Document.id == uuid_a, Document.org_id == org_id)
                    )
                ).scalar_one_or_none()

                # Retrieve document B info and chunks
                doc_b = (
                    await session.execute(
                        select(Document).where(Document.id == uuid_b, Document.org_id == org_id)
                    )
                ).scalar_one_or_none()

                if not doc_a or not doc_b:
                    return ToolResult(
                        tool_name=self.name,
                        success=False,
                        data=None,
                        error="One or both documents not found in organization",
                    )

                # Fetch matching chunks for A
                chunks_a = (
                    (
                        await session.execute(
                            select(DocumentChunk)
                            .where(
                                DocumentChunk.document_id == uuid_a,
                                DocumentChunk.org_id == org_id,
                                DocumentChunk.section_title.ilike(f"%{topic}%"),
                            )
                            .order_by(DocumentChunk.chunk_index.asc())
                        )
                    )
                    .scalars()
                    .all()
                )

                # Fetch matching chunks for B
                chunks_b = (
                    (
                        await session.execute(
                            select(DocumentChunk)
                            .where(
                                DocumentChunk.document_id == uuid_b,
                                DocumentChunk.org_id == org_id,
                                DocumentChunk.section_title.ilike(f"%{topic}%"),
                            )
                            .order_by(DocumentChunk.chunk_index.asc())
                        )
                    )
                    .scalars()
                    .all()
                )

                text_a = (
                    "\n\n".join(c.content for c in chunks_a)
                    if chunks_a
                    else "No matching section found."
                )
                text_b = (
                    "\n\n".join(c.content for c in chunks_b)
                    if chunks_b
                    else "No matching section found."
                )

                return ToolResult(
                    tool_name=self.name,
                    success=True,
                    data={
                        "topic": topic,
                        "document_a": {
                            "id": str(doc_a.id),
                            "title": doc_a.title,
                            "section_found": bool(chunks_a),
                            "content": text_a,
                        },
                        "document_b": {
                            "id": str(doc_b.id),
                            "title": doc_b.title,
                            "section_found": bool(chunks_b),
                            "content": text_b,
                        },
                    },
                )

            except Exception as e:
                logger.error("compare_documents tool error", error=str(e), org_id=str(org_id))
                return ToolResult(tool_name=self.name, success=False, data=None, error=str(e))
