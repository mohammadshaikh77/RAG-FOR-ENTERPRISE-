"""Unit and integration tests for AgentLoop execution, bounding, and refusal."""

import json
import uuid
from typing import Any

import pytest
from agent.citations import is_refusal
from agent.loop import AgentLoop
from agent.tools.calculator import CalculatorTool
from agent.tools.search import SearchDocumentsTool
from llm.gateway import LLMGateway
from llm.providers.base import BaseLLMProvider
from llm.providers.mock import MockLLMProvider
from llm.types import (
    ChatMessage,
    FunctionCall,
    LLMResponse,
    TokenUsage,
    ToolCall,
    ToolDefinition,
)
from sqlalchemy import select

from apps.api.src.db.session import async_session_maker
from apps.api.src.models.agent_trace import AgentTrace
from packages.rag.src.rag.embeddings import MockEmbedder
from packages.rag.src.rag.search import HybridRetriever


class InfiniteLoopMockProvider(BaseLLMProvider):
    """Mock provider that continuously demands tool calls to test step limit enforcement."""

    def __init__(self) -> None:
        super().__init__(name="infinite_mock", model="mock-loop-v1")
        self.steps_called = 0

    def is_available(self) -> bool:
        return True

    async def generate(self, messages: list[ChatMessage], **kwargs: Any) -> LLMResponse:
        return LLMResponse(content="Final answer", provider=self.name, model=self.model)

    async def generate_with_tools(
        self, messages: list[ChatMessage], tools: list[ToolDefinition], **kwargs: Any
    ) -> LLMResponse:
        self.steps_called += 1
        return LLMResponse(
            content=None,
            tool_calls=[
                ToolCall(
                    id=f"call_{self.steps_called}",
                    type="function",
                    function=FunctionCall(
                        name="calculator",
                        arguments=json.dumps({"expression": "1 + 1"}),
                    ),
                )
            ],
            provider=self.name,
            model=self.model,
            usage=TokenUsage(prompt_tokens=10, completion_tokens=5, total_tokens=15),
        )


@pytest.mark.asyncio
async def test_agent_loop_bounded_steps() -> None:
    """Verifies that the agent loop halts strictly when max_steps is reached."""
    infinite_provider = InfiniteLoopMockProvider()
    gateway = LLMGateway(providers=[infinite_provider], enable_cache=False)
    calc_tool = CalculatorTool()
    demo_org_id = uuid.UUID("00000000-0000-0000-0000-000000000001")

    loop = AgentLoop(
        gateway=gateway,
        tools=[calc_tool],
        session_factory=async_session_maker,
        max_steps=3,
    )

    response = await loop.run(org_id=demo_org_id, query="Calculate forever")

    assert infinite_provider.steps_called == 3
    assert response.steps_count == 3
    assert "step limit" in response.final_answer.lower()


@pytest.mark.asyncio
async def test_agent_refusal_on_unanswerable_query() -> None:
    """Verifies that unanswerable queries produce a grounded refusal response."""
    mock = MockLLMProvider()
    gateway = LLMGateway(providers=[mock], enable_cache=False)
    calc_tool = CalculatorTool()
    demo_org_id = uuid.UUID("00000000-0000-0000-0000-000000000001")

    loop = AgentLoop(
        gateway=gateway,
        tools=[calc_tool],
        session_factory=async_session_maker,
        max_steps=5,
    )

    response = await loop.run(
        org_id=demo_org_id,
        query="What is the dosage of martian-fake-drug-xyz?",
    )

    assert response.refused is True
    assert is_refusal(response.final_answer)


@pytest.mark.asyncio
async def test_agent_trace_recorded_in_database() -> None:
    """Verifies that full reasoning trace, citations, and metrics are saved to PostgreSQL."""
    embedder = MockEmbedder()
    retriever = HybridRetriever(embedder=embedder)
    search_tool = SearchDocumentsTool(retriever=retriever, session_factory=async_session_maker)
    calc_tool = CalculatorTool()

    mock = MockLLMProvider()
    gateway = LLMGateway(providers=[mock], enable_cache=False)
    demo_org_id = uuid.UUID("00000000-0000-0000-0000-000000000001")

    loop = AgentLoop(
        gateway=gateway,
        tools=[search_tool, calc_tool],
        session_factory=async_session_maker,
        max_steps=5,
    )

    query = "What is the boxed warning for Lisinopril?"
    response = await loop.run(org_id=demo_org_id, query=query)

    assert response.trace_id is not None
    assert response.tokens_total > 0
    assert len(response.citations) > 0

    # Query DB to inspect persisted trace
    async with async_session_maker() as session:
        trace_uuid = uuid.UUID(response.trace_id)
        stmt = select(AgentTrace).where(AgentTrace.id == trace_uuid)
        res = await session.execute(stmt)
        trace_record = res.scalar_one_or_none()

        assert trace_record is not None
        assert trace_record.org_id == demo_org_id
        assert trace_record.query == query
        assert trace_record.tool_calls_count >= 1
        assert len(trace_record.steps) >= 1
        assert len(trace_record.citations) >= 1
        assert trace_record.tokens_total == response.tokens_total
