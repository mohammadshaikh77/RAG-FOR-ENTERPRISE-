"""Unit tests for LLM Gateway, providers, rate-limiting, and caching."""

from typing import Any

import pytest
from llm.cache import LLMCache
from llm.gateway import LLMGateway
from llm.providers.base import BaseLLMProvider
from llm.providers.mock import MockLLMProvider
from llm.rate_limiter import TokenBucketLimiter
from llm.types import (
    ChatMessage,
    FunctionDefinition,
    LLMResponse,
    ToolDefinition,
)


class FailingProvider(BaseLLMProvider):
    """Provider that deliberately fails to test failover."""

    def __init__(self, name: str = "failing") -> None:
        super().__init__(name=name, model="fail-model")
        self.call_count = 0

    def is_available(self) -> bool:
        return True

    async def generate(self, messages: list[ChatMessage], **kwargs: Any) -> LLMResponse:
        self.call_count += 1
        raise ConnectionError("Simulated provider outage / 429 rate limit")

    async def generate_with_tools(
        self, messages: list[ChatMessage], tools: list[ToolDefinition], **kwargs: Any
    ) -> LLMResponse:
        self.call_count += 1
        raise ConnectionError("Simulated provider outage / 429 rate limit")


class UnavailableProvider(BaseLLMProvider):
    """Provider with no API key configured."""

    def __init__(self) -> None:
        super().__init__(name="unconfigured", model="unavail-model")

    def is_available(self) -> bool:
        return False

    async def generate(self, messages: list[ChatMessage], **kwargs: Any) -> LLMResponse:
        raise RuntimeError("Should not be called")

    async def generate_with_tools(
        self, messages: list[ChatMessage], tools: list[ToolDefinition], **kwargs: Any
    ) -> LLMResponse:
        raise RuntimeError("Should not be called")


@pytest.mark.asyncio
async def test_token_bucket_limiter() -> None:
    limiter = TokenBucketLimiter(requests_per_minute=600, name="test_limiter")
    # Should acquire without error
    await limiter.acquire(1.0)
    assert limiter.tokens < limiter.capacity


@pytest.mark.asyncio
async def test_mock_llm_provider_generation() -> None:
    mock = MockLLMProvider()
    messages = [
        ChatMessage(role="system", content="You are a clinical assistant."),
        ChatMessage(role="user", content="What is lisinopril?"),
    ]
    resp = await mock.generate(messages)
    assert resp.content is not None
    assert "Mock synthesis for: What is lisinopril?" in resp.content
    assert resp.provider == "mock"
    assert resp.usage.total_tokens > 0


@pytest.mark.asyncio
async def test_mock_llm_provider_tool_calling() -> None:
    mock = MockLLMProvider()
    tools = [
        ToolDefinition(
            function=FunctionDefinition(
                name="search_documents",
                description="Search documents",
                parameters={"type": "object", "properties": {"query": {"type": "string"}}},
            )
        )
    ]
    messages = [ChatMessage(role="user", content="Contraindications of metoprolol")]

    # Step 1: Mock should call search_documents
    step1_resp = await mock.generate_with_tools(messages, tools)
    assert len(step1_resp.tool_calls) == 1
    assert step1_resp.tool_calls[0].function.name == "search_documents"
    args = step1_resp.tool_calls[0].get_parsed_arguments()
    assert args.get("query") == "Contraindications of metoprolol"

    # Step 2: Feed back tool result, Mock should produce citation answer
    messages.append(
        ChatMessage(
            role="assistant",
            tool_calls=step1_resp.tool_calls,
        )
    )
    messages.append(
        ChatMessage(
            role="tool",
            tool_call_id=step1_resp.tool_calls[0].id,
            name="search_documents",
            content="Metoprolol is contraindicated in severe bradycardia and cardiogenic shock.",
        )
    )

    step2_resp = await mock.generate_with_tools(messages, tools)
    assert len(step2_resp.tool_calls) == 0
    assert step2_resp.content is not None
    assert "Sources:" in step2_resp.content


@pytest.mark.asyncio
async def test_llm_gateway_failover() -> None:
    failing = FailingProvider("primary_failing")
    mock_fallback = MockLLMProvider("fallback_mock")
    gateway = LLMGateway(providers=[failing, mock_fallback], enable_cache=False)

    messages = [ChatMessage(role="user", content="Explain boxed warning")]
    resp = await gateway.generate(messages)

    assert failing.call_count == 1
    assert mock_fallback.call_count == 1
    assert resp.provider == "mock"
    assert "Mock synthesis" in (resp.content or "")


@pytest.mark.asyncio
async def test_llm_gateway_caching() -> None:
    mock = MockLLMProvider()
    cache = LLMCache()
    gateway = LLMGateway(providers=[mock], cache=cache, enable_cache=True)

    messages = [ChatMessage(role="user", content="What is the dosage of amlodipine?")]
    # First call - cache miss
    resp1 = await gateway.generate(messages, temperature=0.0)
    assert mock.call_count == 1

    # Second identical call - cache hit
    resp2 = await gateway.generate(messages, temperature=0.0)
    assert mock.call_count == 1  # Did not call provider again
    assert resp2.content == resp1.content
