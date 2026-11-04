"""Tool for retrieving an entire designated section of a document."""

import uuid
from typing import Any

import structlog
from sqlalchemy import select

from agent.tools.base import BaseTool, ToolResult
from apps.api.src.models.chunk import DocumentChunk
from apps.api.src.models.document import Document

logger = structlog.get_logger(__name__)


class GetSectionTool(BaseTool):
    """Retrieves full text for a designated clinical section within a document."""

    name = "get_section"
    description = (
        "Retrieve the complete, unabridged text of a specific section (e.g. 'Boxed Warning', "
        "'Contraindications', 'Dosage and Administration', 'Drug Interactions') from a known document ID."
    )
    parameters = {
        "type": "object",
        "properties": {
            "document_id": {
                "type": "string",
                "description": "The UUID of the target document",
            },
            "section_name": {
                "type": "string",
                "description": "Name or keyword of the section (e.g., 'Boxed Warning', 'Contraindications', 'Adverse Reactions')",
            },
        },
        "required": ["document_id", "section_name"],
    }

    def __init__(self, session_factory: Any) -> None:
        self.session_factory = session_factory

    async def execute(self, org_id: uuid.UUID, **kwargs: Any) -> ToolResult:
        doc_id_raw = kwargs.get("document_id")
        section_name = kwargs.get("section_name", "").strip()

        if not doc_id_raw or not section_name:
            return ToolResult(
                tool_name=self.name,
                success=False,
                data=None,
                error="Both document_id and section_name are required",
            )

        try:
            doc_uuid = uuid.UUID(doc_id_raw)
        except ValueError:
            return ToolResult(
                tool_name=self.name, success=False, data=None, error=f"Invalid UUID: {doc_id_raw}"
            )

        async with self.session_factory() as session:
            try:
                # Verify document exists and belongs to org
                doc_stmt = select(Document).where(
                    Document.id == doc_uuid, Document.org_id == org_id
                )
                doc_res = await session.execute(doc_stmt)
                doc = doc_res.scalar_one_or_none()
                if not doc:
                    return ToolResult(
                        tool_name=self.name, success=False, data=None, error="Document not found"
                    )

                # Retrieve matching chunks
                chunks_stmt = (
                    select(DocumentChunk)
                    .where(
                        DocumentChunk.document_id == doc_uuid,
                        DocumentChunk.org_id == org_id,
                        DocumentChunk.section_title.ilike(f"%{section_name}%"),
                    )
                    .order_by(DocumentChunk.chunk_index.asc())
                )
                chunk_res = await session.execute(chunks_stmt)
                chunks = chunk_res.scalars().all()

                if not chunks:
                    return ToolResult(
                        tool_name=self.name,
                        success=True,
                        data={
                            "document_id": str(doc.id),
                            "document_title": doc.title,
                            "section_found": False,
                            "message": f"Section matching '{section_name}' was not found in document.",
                        },
                    )

                full_text = "\n\n".join(c.content for c in chunks)
                return ToolResult(
                    tool_name=self.name,
                    success=True,
                    data={
                        "document_id": str(doc.id),
                        "document_title": doc.title,
                        "section_title": chunks[0].section_title,
                        "section_path": chunks[0].section_path,
                        "content": full_text,
                        "chunk_count": len(chunks),
                    },
                )

            except Exception as e:
                logger.error("get_section tool error", error=str(e), org_id=str(org_id))
                return ToolResult(tool_name=self.name, success=False, data=None, error=str(e))
