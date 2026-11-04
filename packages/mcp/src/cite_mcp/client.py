"""Lightweight MCP client for interacting with the Cite MCP server."""

from typing import Any

import mcp.types as types
from mcp.server.mcpserver import MCPServer


class CiteMCPClient:
    """In-process and programmatic client for the Cite MCP server."""

    def __init__(self, server: MCPServer) -> None:
        self.server = server

    async def list_tools(self) -> list[types.Tool]:
        """Lists all registered tools on the MCP server."""
        return await self.server.list_tools()

    async def call_tool(self, name: str, arguments: dict[str, Any] | None = None) -> str:
        """Executes a tool on the MCP server and returns the text response."""
        res = await self.server.call_tool(name, arguments or {})
        if hasattr(res, "content") and res.content:
            text_parts = [item.text for item in res.content if hasattr(item, "text")]
            return "\n".join(text_parts)
        if isinstance(res, str):
            return res
        return str(res)

    async def search(
        self,
        query: str,
        top_k: int = 5,
        section_filter: str | None = None,
        tenant_id: str | None = None,
    ) -> str:
        """Helper to invoke cite_search."""
        args: dict[str, Any] = {"query": query, "top_k": top_k}
        if section_filter:
            args["section_filter"] = section_filter
        if tenant_id:
            args["tenant_id"] = tenant_id
        return await self.call_tool("cite_search", args)

    async def get_section(
        self,
        document_id_or_title: str,
        section_title: str,
        tenant_id: str | None = None,
    ) -> str:
        """Helper to invoke cite_get_section."""
        args: dict[str, Any] = {
            "document_id_or_title": document_id_or_title,
            "section_title": section_title,
        }
        if tenant_id:
            args["tenant_id"] = tenant_id
        return await self.call_tool("cite_get_section", args)

    async def compare_drugs(
        self,
        drug_a: str,
        drug_b: str,
        aspect: str = "indications",
        tenant_id: str | None = None,
    ) -> str:
        """Helper to invoke cite_compare_drugs."""
        args: dict[str, Any] = {
            "drug_a": drug_a,
            "drug_b": drug_b,
            "aspect": aspect,
        }
        if tenant_id:
            args["tenant_id"] = tenant_id
        return await self.call_tool("cite_compare_drugs", args)

    async def query_structured(
        self,
        query_type: str = "list_drugs",
        drug_class: str | None = None,
        boxed_warning_only: bool = False,
        tenant_id: str | None = None,
    ) -> str:
        """Helper to invoke cite_query_structured."""
        args: dict[str, Any] = {
            "query_type": query_type,
            "boxed_warning_only": boxed_warning_only,
        }
        if drug_class:
            args["drug_class"] = drug_class
        if tenant_id:
            args["tenant_id"] = tenant_id
        return await self.call_tool("cite_query_structured", args)
