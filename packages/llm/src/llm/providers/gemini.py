"""Google Gemini provider adapter using the official OpenAI-compatible endpoint."""

import asyncio
from typing import Any

import httpx
import structlog
from llm.providers.base import BaseLLMProvider
from llm.rate_limiter import TokenBucketLimiter
from llm.types import ChatMessage, FunctionCall, LLMResponse, TokenUsage, ToolCall, ToolDefinition

logger = structlog.get_logger(__name__)


class GeminiProvider(BaseLLMProvider):
    """Google Gemini provider with rate limiting and exponential backoff."""

    def __init__(
        self,
        api_key: str,
        model: str = "gemini-1.5-flash",
        base_url: str = "https://generativelanguage.googleapis.com/v1beta/openai",
        rate_limit_rpm: int = 12,
        timeout: float = 30.0,
    ) -> None:
        super().__init__(name="gemini", model=model)
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.rate_limiter = TokenBucketLimiter(requests_per_minute=rate_limit_rpm, name="gemini")

    def is_available(self) -> bool:
        return bool(self.api_key and self.api_key.strip())

    async def _send_request(
        self,
        messages: list[ChatMessage],
        tools: list[ToolDefinition] | None = None,
        temperature: float = 0.0,
        max_tokens: int | None = None,
        max_retries: int = 2,
    ) -> LLMResponse:
        if not self.is_available():
            raise RuntimeError("GeminiProvider is not configured: GEMINI_API_KEY is missing.")

        url = f"{self.base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
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

        for attempt in range(max_retries + 1):
            await self.rate_limiter.acquire()
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    resp = await client.post(url, headers=headers, json=payload)

                    if resp.status_code == 429:
                        retry_after = float(resp.headers.get("Retry-After", 4.0 * (attempt + 1)))
                        logger.warning(
                            "Gemini rate limit 429 encountered, backing off",
                            attempt=attempt,
                            retry_after=retry_after,
                        )
                        if attempt < max_retries:
                            await asyncio.sleep(retry_after)
                            continue
                        resp.raise_for_status()

                    resp.raise_for_status()
                    data = resp.json()
                    return self._parse_response(data)

            except httpx.HTTPStatusError as e:
                logger.error(
                    "Gemini HTTP error", status=e.response.status_code, body=e.response.text
                )
                raise
            except Exception as e:
                logger.error("Gemini request exception", error=str(e), attempt=attempt)
                if attempt < max_retries:
                    await asyncio.sleep(1.5 * (attempt + 1))
                    continue
                raise

        raise RuntimeError("GeminiProvider exceeded maximum retries")

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
