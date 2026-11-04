"""Cite Model Context Protocol (MCP) Server.

Exposes grounded document search, section retrieval, drug label comparison, and
structured querying tools to external MCP agents (Cursor, Claude Desktop, Antigravity).
Strictly enforces tenant organization isolation on every invocation.
"""

import json
import uuid
from typing import Any

import structlog
from agent.tools.compare import CompareDocumentsTool
from agent.tools.search import SearchDocumentsTool
from agent.tools.section import GetSectionTool
from agent.tools.structured import QueryStructuredDataTool
from mcp.server.mcpserver import MCPServer
from sqlalchemy import select

from apps.api.src.config import get_settings
from apps.api.src.db.session import async_session_maker
from apps.api.src.models.agent_trace import AgentTrace
from cite_mcp.auth import resolve_tenant_id
from packages.rag.src.rag.embeddings import LocalSentenceTransformerEmbedder
from packages.rag.src.rag.search import HybridRetriever

logger = structlog.get_logger(__name__)


def create_mcp_server(
    session_factory: Any = None,
    embedder: Any = None,
    default_tenant_id: uuid.UUID | None = None,
) -> MCPServer:
    """Builds and configures the Cite MCPServer instance with all tools registered."""
    db_factory = session_factory or async_session_maker

    if embedder is None:
        settings = get_settings()
        embedder = LocalSentenceTransformerEmbedder(model_name=settings.embedding_model)

    retriever = HybridRetriever(embedder=embedder)
    search_tool = SearchDocumentsTool(retriever=retriever, session_factory=db_factory)
    section_tool = GetSectionTool(session_factory=db_factory)
    compare_tool = CompareDocumentsTool(session_factory=db_factory)
    structured_tool = QueryStructuredDataTool(session_factory=db_factory)

    mcp_server = MCPServer(
        name="cite-mcp",
        instructions=(
            "Cite Enterprise Document Intelligence MCP Server. Provides grounded retrieval, "
            "section inspection, side-by-side drug comparison, and structured metadata queries "
            "over official FDA drug labels and clinical repository documents. Every result includes "
            "verifiable citation anchors."
        ),
    )

    @mcp_server.tool()
    async def cite_search(
        query: str,
        top_k: int = 5,
        section_filter: str | None = None,
        tenant_id: str | None = None,
    ) -> str:
        """Search tenant clinical documents using hybrid vector semantic and full-text keyword retrieval.

        Args:
            query: Clinical query or question (e.g. 'What are the contraindications for Lisinopril?')
            top_k: Number of relevant chunks to retrieve (1 to 10, default 5)
            section_filter: Optional section title filter (e.g. 'Boxed Warning', 'Contraindications')
            tenant_id: Optional explicit tenant organization UUID (defaults to CITE_TENANT_ID environment variable)

        Returns:
            Grounded search results containing document titles, section paths, scores, and chunk text.
        """
        try:
            org_id = resolve_tenant_id(tenant_id, default_tenant_id)
        except PermissionError as e:
            return f"Authentication Error: {e}"

        res = await search_tool.execute(
            org_id=org_id,
            query=query,
            top_k=min(max(1, top_k), 10),
            section_filter=section_filter,
        )

        if not res.success or not res.data:
            return f"No matching documents found in tenant workspace. Error: {res.error or 'None'}"

        output_lines = [f"Found {len(res.data)} grounded document chunks for: '{query}':\n"]
        for i, chunk in enumerate(res.data, start=1):
            doc_title = chunk.get("document_title", "Unknown Document")
            sec_title = chunk.get("section_title", "General")
            score = chunk.get("score", 0.0)
            content = chunk.get("content", "").strip()

            output_lines.append(
                f"[{i}] [Document: {doc_title} | Section: {sec_title}] (Score: {score:.4f})"
            )
            output_lines.append(f"{content}\n")

        return "\n".join(output_lines)

    @mcp_server.tool()
    async def cite_get_section(
        document_id_or_title: str,
        section_title: str,
        tenant_id: str | None = None,
    ) -> str:
        """Retrieve the exact, full content of a specific section from a document.

        Args:
            document_id_or_title: Document UUID or case-insensitive title prefix (e.g. 'Naproxen')
            section_title: Standard label section heading (e.g. 'Boxed Warning', 'Indications & Usage', 'Dosage & Administration')
            tenant_id: Optional explicit tenant organization UUID (defaults to CITE_TENANT_ID)

        Returns:
            The complete reconstructed text for that clinical section with metadata.
        """
        try:
            org_id = resolve_tenant_id(tenant_id, default_tenant_id)
        except PermissionError as e:
            return f"Authentication Error: {e}"

        # Resolve document_id from UUID or title prefix
        doc_uuid: uuid.UUID | None = None
        try:
            doc_uuid = uuid.UUID(document_id_or_title.strip())
        except ValueError:
            from apps.api.src.models.document import Document

            async with db_factory() as session:
                stmt = (
                    select(Document.id)
                    .where(
                        Document.org_id == org_id,
                        Document.title.ilike(f"%{document_id_or_title.strip()}%"),
                    )
                    .limit(1)
                )
                doc_uuid = (await session.execute(stmt)).scalar_one_or_none()

        if not doc_uuid:
            return f"Section not found: Could not find document matching '{document_id_or_title}' in tenant workspace"

        res = await section_tool.execute(
            org_id=org_id,
            document_id=str(doc_uuid),
            section_name=section_title,
        )

        if not res.success or not res.data:
            return f"Section not found: {res.error or 'No matching section in specified document'}"

        data = res.data
        doc_title = data.get("document_title", document_id_or_title)
        sec_title = data.get("section_title", section_title)
        content = data.get("content", "")
        chunks_count = data.get("chunks_count", 1)

        return (
            f"=== [Document: {doc_title} | Section: {sec_title}] ({chunks_count} chunks) ===\n\n"
            f"{content}"
        )

    @mcp_server.tool()
    async def cite_compare_drugs(
        drug_a: str,
        drug_b: str,
        aspect: str = "indications",
        tenant_id: str | None = None,
    ) -> str:
        """Compare specific clinical aspects between two approved drug labels side-by-side.

        Args:
            drug_a: Name or document title of the first drug (e.g. 'Naproxen')
            drug_b: Name or document title of the second drug (e.g. 'Celecoxib')
            aspect: Clinical aspect to compare ('indications', 'warnings', 'adverse_reactions', 'dosage', 'contraindications')
            tenant_id: Optional explicit tenant organization UUID (defaults to CITE_TENANT_ID)

        Returns:
            Side-by-side comparison text with evidence from both document labels.
        """
        try:
            org_id = resolve_tenant_id(tenant_id, default_tenant_id)
        except PermissionError as e:
            return f"Authentication Error: {e}"

        from apps.api.src.models.document import Document

        async def resolve_doc_id(name_or_id: str) -> uuid.UUID | None:
            try:
                return uuid.UUID(name_or_id.strip())
            except ValueError:
                async with db_factory() as session:
                    stmt = (
                        select(Document.id)
                        .where(
                            Document.org_id == org_id,
                            Document.title.ilike(f"%{name_or_id.strip()}%"),
                        )
                        .limit(1)
                    )
                    return (await session.execute(stmt)).scalar_one_or_none()

        id_a = await resolve_doc_id(drug_a)
        id_b = await resolve_doc_id(drug_b)

        if not id_a or not id_b:
            missing = []
            if not id_a:
                missing.append(drug_a)
            if not id_b:
                missing.append(drug_b)
            return f"Comparison failed: Documents not found in workspace: {', '.join(missing)}"

        res = await compare_tool.execute(
            org_id=org_id,
            doc_a_id=str(id_a),
            doc_b_id=str(id_b),
            topic=aspect,
        )

        if not res.success or not res.data:
            return f"Comparison failed: {res.error or 'Could not locate matching drugs'}"

        data = res.data
        a_info = data.get(drug_a) or data.get(str(id_a)) or {}
        b_info = data.get(drug_b) or data.get(str(id_b)) or {}

        lines = [
            f"=== Comparative Clinical Analysis: {drug_a} vs {drug_b} ({aspect.upper()}) ===\n",
            f"--- {drug_a} ({a_info.get('section_found', 'Section N/A')}) ---",
            str(a_info.get("content", "No content found for specified aspect.")).strip(),
            f"\n--- {drug_b} ({b_info.get('section_found', 'Section N/A')}) ---",
            str(b_info.get("content", "No content found for specified aspect.")).strip(),
        ]
        return "\n".join(lines)

    @mcp_server.tool()
    async def cite_query_structured(
        query_type: str = "list_drugs",
        drug_class: str | None = None,
        boxed_warning_only: bool = False,
        tenant_id: str | None = None,
    ) -> str:
        """Query structured tabular drug label metadata extracted during document ingestion.

        Args:
            query_type: Query type ('list_drugs', 'list_classes', 'filter_by_class', 'filter_by_boxed_warning', 'find_drugs')
            drug_class: Pharmacologic class filter (e.g. 'NSAID', 'ACE Inhibitor', 'Beta Blocker')
            boxed_warning_only: If True, restricts results to drugs carrying an active FDA Boxed Warning
            tenant_id: Optional explicit tenant organization UUID (defaults to CITE_TENANT_ID)

        Returns:
            Structured clinical metadata formatted as JSON.
        """
        try:
            org_id = resolve_tenant_id(tenant_id, default_tenant_id)
        except PermissionError as e:
            return f"Authentication Error: {e}"

        # Map friendly query types to QueryStructuredDataTool parameters
        actual_query_type = query_type
        params: dict[str, Any] = {}

        if query_type in ("list_drugs", "find_drugs"):
            actual_query_type = "find_drugs"
            if boxed_warning_only:
                params["has_boxed_warning"] = True
            if drug_class:
                params["drug_class"] = drug_class
        elif query_type == "filter_by_boxed_warning" or (query_type == "list_boxed_warnings"):
            actual_query_type = "filter_by_boxed_warning"
            params["has_boxed_warning"] = True
        elif query_type == "filter_by_class" or (drug_class and query_type != "list_classes"):
            actual_query_type = "filter_by_class"
            params["drug_class"] = drug_class
        elif query_type == "list_classes":
            actual_query_type = "list_classes"

        res = await structured_tool.execute(
            org_id=org_id,
            query_type=actual_query_type,
            parameters=params,
        )

        if not res.success:
            return f"Structured query error: {res.error}"

        return json.dumps(res.data, indent=2)

    @mcp_server.tool()
    async def cite_audit_trace(
        trace_id: str,
        tenant_id: str | None = None,
    ) -> str:
        """Inspect execution audit trace telemetry for a previous agent query.

        Args:
            trace_id: Unique trace UUID
            tenant_id: Optional explicit tenant organization UUID (defaults to CITE_TENANT_ID)

        Returns:
            JSON representation of the trace execution steps, token usage, latency, and citations.
        """
        try:
            org_id = resolve_tenant_id(tenant_id, default_tenant_id)
            trace_uuid = uuid.UUID(trace_id.strip())
        except (ValueError, PermissionError) as e:
            return f"Error: {e}"

        async with db_factory() as session:
            stmt = select(AgentTrace).where(
                AgentTrace.id == trace_uuid,
                AgentTrace.org_id == org_id,
            )
            result = await session.execute(stmt)
            trace = result.scalar_one_or_none()

            if not trace:
                return f"Trace not found for ID: {trace_id} in tenant workspace."

            trace_data = {
                "trace_id": str(trace.id),
                "query": trace.query,
                "final_answer": trace.final_answer,
                "refused": trace.refused,
                "provider": trace.provider,
                "model": trace.model,
                "tokens_prompt": trace.tokens_prompt,
                "tokens_completion": trace.tokens_completion,
                "tokens_total": trace.tokens_total,
                "latency_ms": trace.latency_ms,
                "tool_calls_count": trace.tool_calls_count,
                "citations": trace.citations,
                "created_at": trace.created_at.isoformat() if trace.created_at else None,
            }
            return json.dumps(trace_data, indent=2)

    return mcp_server
