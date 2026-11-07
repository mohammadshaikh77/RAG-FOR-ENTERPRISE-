"""Tool for searching tenant clinical documents using hybrid vector + full-text retrieval."""

import uuid
from typing import Any

import structlog

from agent.tools.base import BaseTool, ToolResult
from packages.rag.src.rag.search import HybridRetriever, RetrievalMode

logger = structlog.get_logger(__name__)


class SearchDocumentsTool(BaseTool):
    """Hybrid semantic and keyword document search tool."""

    name = "search_documents"
    description = (
        "Search through clinical drug labels, package inserts, and documents. "
        "Returns the most relevant text chunks along with section headings and citation metadata. "
        "Use this as your primary tool when looking up specific facts, indications, adverse events, or warnings."
    )
    parameters = {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "The search query (e.g., 'What are the contraindications of metoprolol?')",
            },
            "section_filter": {
                "type": "string",
                "description": "Optional section title filter (e.g., 'Boxed Warning', 'Contraindications', 'Adverse Reactions')",
            },
            "top_k": {
                "type": "integer",
                "description": "Number of relevant chunks to retrieve (default: 5, max: 10)",
                "default": 5,
            },
        },
        "required": ["query"],
    }

    def __init__(
        self,
        retriever: HybridRetriever,
        session_factory: Any,
    ) -> None:
        self.retriever = retriever
        self.session_factory = session_factory

    async def execute(self, org_id: uuid.UUID, **kwargs: Any) -> ToolResult:
        query = kwargs.get("query", "")
        if not query:
            return ToolResult(
                tool_name=self.name,
                success=False,
                data=[],
                error="Missing required query parameter",
            )

        section_filter = kwargs.get("section_filter")
        top_k = min(int(kwargs.get("top_k", 5)), 10)

        async with self.session_factory() as session:
            try:
                results = await self.retriever.search(
                    session=session,
                    org_id=org_id,
                    query=query,
                    top_k=top_k,
                    candidate_k=20,
                    mode=RetrievalMode.HYBRID_RERANK,
                    section=section_filter,
                )

                formatted = [
                    {
                        "chunk_id": str(r.chunk_id),
                        "document_id": str(r.document_id),
                        "document_title": r.document_title,
                        "section_title": r.section_title,
                        "content": r.content,
                        "score": round(r.score, 4),
                        "is_flagged_injection": bool(r.metadata.get("is_flagged_injection", False)),
                    }
                    for r in results
                ]

                return ToolResult(tool_name=self.name, success=True, data=formatted)

            except Exception as e:
                logger.error(
                    "search_documents tool execution error", error=str(e), org_id=str(org_id)
                )
                return ToolResult(tool_name=self.name, success=False, data=[], error=str(e))
