"""Ollama local provider adapter for running open-source models offline."""

from typing import Any

import httpx
import structlog
from llm.providers.base import BaseLLMProvider
from llm.types import ChatMessage, FunctionCall, LLMResponse, TokenUsage, ToolCall, ToolDefinition

logger = structlog.get_logger(__name__)


class OllamaProvider(BaseLLMProvider):
    """Local Ollama provider using standard /v1 OpenAI-compatible endpoints."""

    def __init__(
        self,
        base_url: str = "http://localhost:11434",
        model: str = "llama3.1:8b",
        timeout: float = 60.0,
    ) -> None:
        super().__init__(name="ollama", model=model)
        self.base_url = f"{base_url.rstrip('/')}/v1"
        self.timeout = timeout

    def is_available(self) -> bool:
        # Check if Ollama server is reachable
        try:
            with httpx.Client(timeout=1.0) as client:
                res = client.get(f"{self.base_url}/models")
                return res.status_code == 200
        except Exception:
            return False

    async def _send_request(
        self,
        messages: list[ChatMessage],
        tools: list[ToolDefinition] | None = None,
        temperature: float = 0.0,
        max_tokens: int | None = None,
    ) -> LLMResponse:
        url = f"{self.base_url}/chat/completions"
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": [m.to_api_dict() for m in messages],
            "temperature": temperature,
        }
        if max_tokens is not None:
            payload["max_tokens"] = max_tokens
        if tools:
            payload["tools"] = [t.to_api_dict() for t in tools]
            payload["tool_choice"] = "auto"

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.post(url, json=payload)
            resp.raise_for_status()
            data = resp.json()
            return self._parse_response(data)

    def _parse_response(self, data: dict[str, Any]) -> LLMResponse:
        choice = data.get("choices", [{}])[0]
        message = choice.get("message", {})
        content = message.get("content")
        finish_reason = choice.get("finish_reason", "stop")

        raw_tool_calls = message.get("tool_calls", [])
        tool_calls: list[ToolCall] = []
        for tc in raw_tool_calls:
            fn = tc.get("function", {})
            tool_calls.append(
                ToolCall(
                    id=tc.get("id", f"call_{len(tool_calls)}"),
                    type="function",
                    function=FunctionCall(
                        name=fn.get("name", ""),
                        arguments=fn.get("arguments", "{}"),
                    ),
                )
            )

        raw_usage = data.get("usage", {})
        usage = TokenUsage(
            prompt_tokens=raw_usage.get("prompt_tokens", 0),
            completion_tokens=raw_usage.get("completion_tokens", 0),
            total_tokens=raw_usage.get("total_tokens", 0),
        )

        return LLMResponse(
            content=content,
            tool_calls=tool_calls,
            provider=self.name,
            model=self.model,
            usage=usage,
            finish_reason=finish_reason,
            raw_response=data,
        )

    async def generate(
        self,
        messages: list[ChatMessage],
        temperature: float = 0.0,
        max_tokens: int | None = None,
        **kwargs: Any,
    ) -> LLMResponse:
        return await self._send_request(
            messages=messages,
            tools=None,
            temperature=temperature,
            max_tokens=max_tokens,
        )

    async def generate_with_tools(
        self,
        messages: list[ChatMessage],
        tools: list[ToolDefinition],
        temperature: float = 0.0,
        max_tokens: int | None = None,
        **kwargs: Any,
    ) -> LLMResponse:
        return await self._send_request(
            messages=messages,
            tools=tools,
            temperature=temperature,
            max_tokens=max_tokens,
        )
