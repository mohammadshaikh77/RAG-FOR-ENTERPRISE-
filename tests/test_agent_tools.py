"""Unit and integration tests for Agent tools."""

import uuid

import pytest
from agent.tools.calculator import CalculatorTool
from agent.tools.compare import CompareDocumentsTool
from agent.tools.search import SearchDocumentsTool
from agent.tools.section import GetSectionTool
from agent.tools.structured import QueryStructuredDataTool

from apps.api.src.db.session import async_session_maker
from packages.rag.src.rag.embeddings import MockEmbedder
from packages.rag.src.rag.search import HybridRetriever


@pytest.mark.asyncio
async def test_calculator_tool_arithmetic() -> None:
    calc = CalculatorTool()
    dummy_org = uuid.uuid4()

    # Basic arithmetic
    r1 = await calc.execute(dummy_org, expression="150 + 25 * 2")
    assert r1.success is True
    assert r1.data["result"] == 200

    # Division and float
    r2 = await calc.execute(dummy_org, expression="10 / 4")
    assert r2.success is True
    assert r2.data["result"] == 2.5

    # Power
    r3 = await calc.execute(dummy_org, expression="2 ** 3")
    assert r3.success is True
    assert r3.data["result"] == 8

    # Division by zero
    r4 = await calc.execute(dummy_org, expression="10 / 0")
    assert r4.success is False
    assert "Division by zero" in (r4.error or "")

    # Security check: Arbitrary code execution / system access
    r5 = await calc.execute(dummy_org, expression="__import__('os').system('ls')")
    assert r5.success is False
    assert "Disallowed expression syntax" in (r5.error or "")

    # Empty expression
    r6 = await calc.execute(dummy_org, expression="")
    assert r6.success is False


@pytest.mark.asyncio
async def test_query_structured_data_tool() -> None:
    tool = QueryStructuredDataTool(session_factory=async_session_maker)
    demo_org_id = uuid.UUID("00000000-0000-0000-0000-000000000001")

    # 1. list_classes
    res1 = await tool.execute(demo_org_id, query_type="list_classes")
    assert res1.success is True
    assert isinstance(res1.data, list)
    assert len(res1.data) > 0

    # 2. filter_by_boxed_warning
    res2 = await tool.execute(
        demo_org_id,
        query_type="filter_by_boxed_warning",
        parameters={"has_boxed_warning": True},
    )
    assert res2.success is True
    assert len(res2.data) > 0
    for drug in res2.data:
        assert drug["has_boxed_warning"] is True

    # 3. get_drug_info
    res3 = await tool.execute(
        demo_org_id,
        query_type="get_drug_info",
        parameters={"drug_name": "metoprolol"},
    )
    assert res3.success is True
    assert len(res3.data) > 0
    assert "METOPROLOL" in res3.data[0]["drug_name"].upper()

    # 4. find_drugs
    res4 = await tool.execute(
        demo_org_id,
        query_type="find_drugs",
        parameters={"route": "ORAL", "has_boxed_warning": True},
    )
    assert res4.success is True
    assert len(res4.data) > 0

    # 5. Invalid query type
    res5 = await tool.execute(demo_org_id, query_type="arbitrary_unsupported")
    assert res5.success is False


@pytest.mark.asyncio
async def test_search_and_section_tools() -> None:
    embedder = MockEmbedder()
    retriever = HybridRetriever(embedder=embedder)
    search_tool = SearchDocumentsTool(retriever=retriever, session_factory=async_session_maker)
    section_tool = GetSectionTool(session_factory=async_session_maker)
    compare_tool = CompareDocumentsTool(session_factory=async_session_maker)

    demo_org_id = uuid.UUID("00000000-0000-0000-0000-000000000001")

    # 1. Search tool
    s_res = await search_tool.execute(demo_org_id, query="hypertension blood pressure", top_k=3)
    assert s_res.success is True
    assert len(s_res.data) > 0
    doc_id = s_res.data[0]["document_id"]

    # 2. Section tool
    sec_res = await section_tool.execute(
        demo_org_id,
        document_id=doc_id,
        section_name="Indications",
    )
    assert sec_res.success is True

    # 3. Compare tool
    comp_res = await compare_tool.execute(
        demo_org_id,
        doc_a_id=doc_id,
        doc_b_id=doc_id,
        topic="Indications",
    )
    assert comp_res.success is True
    assert comp_res.data["document_a"]["id"] == doc_id
