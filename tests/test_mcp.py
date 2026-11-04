"""Comprehensive test suite for Model Context Protocol (MCP) server and client.

Validates tool registration, search, section retrieval, drug comparison,
structured querying, multi-tenant isolation, and stdio client connection.
"""

import json
import os
import sys
import uuid

import pytest
from cite_mcp.client import CiteMCPClient
from cite_mcp.server import create_mcp_server
from mcp.client.session import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client

from apps.api.src.db.session import async_session_maker
from apps.api.src.models.chunk import DocumentChunk
from apps.api.src.models.document import Document, DocumentStatus
from apps.api.src.models.organization import Organization


class MockEmbedder:
    """Deterministic mock embedder for fast, reproducible testing."""

    @property
    def model_name(self) -> str:
        return "mock-embedder-v1"

    @property
    def dimension(self) -> int:
        return 384

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        return [[0.05 * (i % 5) for i in range(384)] for _ in texts]

    def embed_query(self, query: str) -> list[float]:
        return [0.05 * (i % 5) for i in range(384)]


DEMO_ORG_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")


@pytest.fixture
def mcp_client() -> CiteMCPClient:
    """Fixture providing in-process CiteMCPClient with demo org default."""
    server = create_mcp_server(
        session_factory=async_session_maker,
        embedder=MockEmbedder(),
        default_tenant_id=DEMO_ORG_ID,
    )
    return CiteMCPClient(server=server)


@pytest.mark.asyncio
async def test_mcp_server_tool_registration(mcp_client: CiteMCPClient) -> None:
    """Verifies that all 5 required tools are registered with schemas on the MCP server."""
    tools = await mcp_client.list_tools()
    tool_names = {t.name for t in tools}

    expected_tools = {
        "cite_search",
        "cite_get_section",
        "cite_compare_drugs",
        "cite_query_structured",
        "cite_audit_trace",
    }
    assert expected_tools.issubset(tool_names), f"Missing tools. Registered: {tool_names}"

    # Verify cite_search schema
    search_tool = next(t for t in tools if t.name == "cite_search")
    schema = getattr(search_tool, "input_schema", getattr(search_tool, "inputSchema", {}))
    assert "query" in schema.get("properties", {})
    assert "top_k" in schema.get("properties", {})
    assert search_tool.description and "hybrid vector" in search_tool.description


@pytest.mark.asyncio
async def test_mcp_cite_search(mcp_client: CiteMCPClient) -> None:
    """Verifies cite_search executes hybrid retrieval and formats grounded citations."""
    res = await mcp_client.search(
        query="boxed warning naproxen",
        top_k=3,
        tenant_id=str(DEMO_ORG_ID),
    )

    assert isinstance(res, str)
    assert "Found" in res
    assert "[Document:" in res
    assert "Section:" in res


@pytest.mark.asyncio
async def test_mcp_cite_get_section(mcp_client: CiteMCPClient) -> None:
    """Verifies cite_get_section retrieves section content from an ingested label."""
    res = await mcp_client.get_section(
        document_id_or_title="Naproxen",
        section_title="Boxed Warning",
        tenant_id=str(DEMO_ORG_ID),
    )

    assert isinstance(res, str)
    assert "Naproxen" in res
    assert "Boxed Warning" in res


@pytest.mark.asyncio
async def test_mcp_cite_compare_drugs(mcp_client: CiteMCPClient) -> None:
    """Verifies cite_compare_drugs delivers side-by-side comparative analysis."""
    res = await mcp_client.compare_drugs(
        drug_a="Naproxen",
        drug_b="Celecoxib",
        aspect="indications",
        tenant_id=str(DEMO_ORG_ID),
    )

    assert isinstance(res, str)
    assert "Comparative Clinical Analysis" in res
    assert "Naproxen" in res
    assert "Celecoxib" in res


@pytest.mark.asyncio
async def test_mcp_cite_query_structured(mcp_client: CiteMCPClient) -> None:
    """Verifies cite_query_structured returns valid JSON structured metadata."""
    res_str = await mcp_client.query_structured(
        query_type="list_drugs",
        boxed_warning_only=True,
        tenant_id=str(DEMO_ORG_ID),
    )

    assert isinstance(res_str, str)
    parsed = json.loads(res_str)
    assert isinstance(parsed, list)
    assert len(parsed) > 0
    first_drug = parsed[0]
    assert "drug_name" in first_drug
    assert "has_boxed_warning" in first_drug
    assert first_drug["has_boxed_warning"] is True


@pytest.mark.asyncio
async def test_mcp_tenant_isolation() -> None:
    """Adversarial check: Verifies Tenant B cannot search or access Tenant A's documents via MCP."""
    org_a_id = uuid.uuid4()
    org_b_id = uuid.uuid4()

    async with async_session_maker() as session:
        org_a = Organization(id=org_a_id, name="MCP Org A", slug=f"mcp-a-{org_a_id}")
        org_b = Organization(id=org_b_id, name="MCP Org B", slug=f"mcp-b-{org_b_id}")
        session.add_all([org_a, org_b])

        # Confidential document strictly in Tenant A
        doc_a_id = uuid.uuid4()
        confidential_text = "CONFIDENTIAL_FORMULATION_SECRET_XYZ7788: Take 500mg intravenously."
        doc_a = Document(
            id=doc_a_id,
            org_id=org_a_id,
            title="Confidential Compound XYZ-7788",
            file_type="text/plain",
            file_hash=f"hash_{doc_a_id}",
            status=DocumentStatus.COMPLETED,
            chunk_count=1,
        )
        session.add(doc_a)

        chunk_a = DocumentChunk(
            id=uuid.uuid4(),
            document_id=doc_a_id,
            org_id=org_a_id,
            chunk_index=0,
            section_title="Confidential Dosage",
            section_path="Dosage / Secret",
            content=confidential_text,
            token_count=10,
            embedding=[0.05 * (i % 5) for i in range(384)],
        )
        session.add(chunk_a)
        await session.commit()

    server = create_mcp_server(
        session_factory=async_session_maker,
        embedder=MockEmbedder(),
    )
    client = CiteMCPClient(server=server)

    # 1. Tenant B searches for Tenant A's secret formulation
    res_b = await client.search(
        query="CONFIDENTIAL_FORMULATION_SECRET_XYZ7788",
        tenant_id=str(org_b_id),
    )
    assert "XYZ7788" not in res_b
    assert "No matching documents found" in res_b

    # 2. Tenant A searches for its own secret formulation
    res_a = await client.search(
        query="CONFIDENTIAL_FORMULATION_SECRET_XYZ7788",
        tenant_id=str(org_a_id),
    )
    assert "XYZ7788" in res_a
    assert "[Document: Confidential Compound XYZ-7788" in res_a


@pytest.mark.asyncio
async def test_mcp_auth_refusal() -> None:
    """Verifies that unauthenticated calls without tenant identity return Authentication Error."""
    server = create_mcp_server(
        session_factory=async_session_maker,
        embedder=MockEmbedder(),
        default_tenant_id=None,
    )
    client = CiteMCPClient(server=server)

    # Call without any tenant_id provided
    res = await client.search(query="naproxen", tenant_id=None)
    assert "Authentication Error" in res
    assert "No valid tenant organization specified" in res


@pytest.mark.asyncio
async def test_mcp_stdio_client_connection() -> None:
    """Tests full standard I/O (stdio) MCP client connection over subprocess."""
    server_script = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "scripts", "run_mcp_server.py")
    )
    python_bin = sys.executable

    server_params = StdioServerParameters(
        command=python_bin,
        args=[server_script, "--transport", "stdio", "--tenant-id", str(DEMO_ORG_ID)],
        env={
            **os.environ,
            "PYTHONPATH": ".:packages/agent/src:packages/llm/src:packages/rag/src:packages/mcp/src",
            "CITE_TENANT_ID": str(DEMO_ORG_ID),
        },
    )

    async with stdio_client(server_params) as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()

            # Verify tool discovery
            tool_list = await session.list_tools()
            names = [t.name for t in tool_list.tools]
            assert "cite_search" in names
            assert "cite_compare_drugs" in names

            # Execute tool call over stdio transport
            call_res = await session.call_tool(
                name="cite_search",
                arguments={"query": "naproxen boxed warning", "top_k": 2},
            )

            assert call_res.content is not None
            text_blocks = [c.text for c in call_res.content if hasattr(c, "text")]
            combined_text = "\n".join(text_blocks)

            assert "[Document:" in combined_text
            assert "Naproxen" in combined_text
