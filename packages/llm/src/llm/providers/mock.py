"""Deterministic Mock LLM provider for tests, CI, and offline development."""

import json
from collections.abc import Callable
from typing import Any

from llm.providers.base import BaseLLMProvider
from llm.types import ChatMessage, FunctionCall, LLMResponse, TokenUsage, ToolCall, ToolDefinition


class MockLLMProvider(BaseLLMProvider):
    """Configurable mock LLM provider simulating tool use, citations, and refusals."""

    def __init__(
        self,
        model: str = "mock-model-v1",
        custom_handler: Callable[[list[ChatMessage], list[ToolDefinition] | None], LLMResponse]
        | None = None,
    ) -> None:
        super().__init__(name="mock", model=model)
        self.custom_handler = custom_handler
        self.call_count = 0

    def is_available(self) -> bool:
        return True

    async def generate(
        self,
        messages: list[ChatMessage],
        temperature: float = 0.0,
        max_tokens: int | None = None,
        **kwargs: Any,
    ) -> LLMResponse:
        self.call_count += 1
        if self.custom_handler:
            return self.custom_handler(messages, None)

        last_user_msg = next((m.content for m in reversed(messages) if m.role == "user"), "")
        content = f"Mock synthesis for: {last_user_msg}"
        return LLMResponse(
            content=content,
            tool_calls=[],
            provider=self.name,
            model=self.model,
            usage=TokenUsage(prompt_tokens=25, completion_tokens=15, total_tokens=40),
        )

    async def generate_with_tools(
        self,
        messages: list[ChatMessage],
        tools: list[ToolDefinition],
        temperature: float = 0.0,
        max_tokens: int | None = None,
        **kwargs: Any,
    ) -> LLMResponse:
        self.call_count += 1
        if self.custom_handler:
            return self.custom_handler(messages, tools)

        # Check if any tool messages are already in history
        has_tool_results = any(m.role == "tool" for m in messages)
        last_user_msg = next((m.content or "" for m in reversed(messages) if m.role == "user"), "")

        # If user asks an explicitly unanswerable question or mentions "unknown" / "martian"
        if any(
            unans in last_user_msg.lower()
            for unans in ["martian", "unanswerable", "fake-drug-xyz", "not in document"]
        ):
            return LLMResponse(
                content="I cannot answer this question based on the provided documents as no relevant evidence was found.",
                tool_calls=[],
                provider=self.name,
                model=self.model,
                usage=TokenUsage(prompt_tokens=40, completion_tokens=20, total_tokens=60),
            )

        # If tools available and haven't called any tool yet, initiate a tool call
        if tools and not has_tool_results:
            tool_names = [t.function.name for t in tools]
            if "search_documents" in tool_names:
                return LLMResponse(
                    content=None,
                    tool_calls=[
                        ToolCall(
                            id="mock_call_1",
                            type="function",
                            function=FunctionCall(
                                name="search_documents",
                                arguments=json.dumps({"query": last_user_msg, "top_k": 3}),
                            ),
                        )
                    ],
                    provider=self.name,
                    model=self.model,
                    usage=TokenUsage(prompt_tokens=50, completion_tokens=15, total_tokens=65),
                )

        # After tool results are present, synthesize answer with citations
        tool_results = [m.content for m in messages if m.role == "tool"]
        summary = "Based on the retrieved clinical documentation: " + (
            tool_results[0][:200] if tool_results else "No data"
        )

        # Grounded answer with citation format
        cited_answer = (
            f"{summary}\n\n"
            "Sources:\n"
            '- [Document: Lisinopril FDA Label | Section: Boxed Warning | "When used in pregnancy during the second and third trimesters, ACE inhibitors can cause injury and even death to the developing fetus."]'
        )

        return LLMResponse(
            content=cited_answer,
            tool_calls=[],
            provider=self.name,
            model=self.model,
            usage=TokenUsage(prompt_tokens=120, completion_tokens=60, total_tokens=180),
        )
