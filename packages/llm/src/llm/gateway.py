"""Unified LLM Gateway with priority failover, backoff, and caching."""

import time
from typing import Any

import structlog

from llm.cache import LLMCache, generate_cache_key
from llm.providers.base import BaseLLMProvider
from llm.types import ChatMessage, LLMResponse, ToolDefinition

logger = structlog.get_logger(__name__)


class LLMGateway:
    """Manages prioritized failover across multiple LLM providers with automatic caching."""

    def __init__(
        self,
        providers: list[BaseLLMProvider],
        cache: LLMCache | None = None,
        enable_cache: bool = True,
    ) -> None:
        self.providers = providers
        self.cache = cache or LLMCache()
        self.enable_cache = enable_cache

    def get_provider(self, name: str) -> BaseLLMProvider | None:
        for p in self.providers:
            if p.name.lower() == name.lower():
                return p
        return None

    async def generate(
        self,
        messages: list[ChatMessage],
        temperature: float = 0.0,
        max_tokens: int | None = None,
        preferred_provider: str | None = None,
        **kwargs: Any,
    ) -> LLMResponse:
        """Generates completion attempting providers in prioritized order."""
        return await self._execute_with_failover(
            has_tools=False,
            messages=messages,
            tools=None,
            temperature=temperature,
            max_tokens=max_tokens,
            preferred_provider=preferred_provider,
            **kwargs,
        )

    async def generate_with_tools(
        self,
        messages: list[ChatMessage],
        tools: list[ToolDefinition],
        temperature: float = 0.0,
        max_tokens: int | None = None,
        preferred_provider: str | None = None,
        **kwargs: Any,
    ) -> LLMResponse:
        """Generates tool completion attempting providers in prioritized order."""
        return await self._execute_with_failover(
            has_tools=True,
            messages=messages,
            tools=tools,
            temperature=temperature,
            max_tokens=max_tokens,
            preferred_provider=preferred_provider,
            **kwargs,
        )

    async def _execute_with_failover(
        self,
        has_tools: bool,
        messages: list[ChatMessage],
        tools: list[ToolDefinition] | None = None,
        temperature: float = 0.0,
        max_tokens: int | None = None,
        preferred_provider: str | None = None,
        **kwargs: Any,
    ) -> LLMResponse:
        # Determine candidate providers
        candidates: list[BaseLLMProvider] = []
        if preferred_provider:
            match = self.get_provider(preferred_provider)
            if match:
                candidates.append(match)

        for p in self.providers:
            if p not in candidates:
                candidates.append(p)

        last_error: Exception | None = None

        for provider in candidates:
            if not provider.is_available():
                logger.debug("Skipping unconfigured provider", provider=provider.name)
                continue

            cache_key = ""
            # Check cache if enabled and temperature == 0 (deterministic)
            if self.enable_cache and temperature == 0.0:
                cache_key = generate_cache_key(
                    provider=provider.name,
                    model=provider.model,
                    messages=messages,
                    tools=tools,
                    temperature=temperature,
                )
                cached = await self.cache.get(cache_key)
                if cached is not None:
                    logger.info("LLM cache hit", provider=provider.name, model=provider.model)
                    return cached

            start_time = time.monotonic()
            try:
                logger.info(
                    "Calling LLM provider",
                    provider=provider.name,
                    model=provider.model,
                    has_tools=has_tools,
                )
                if has_tools and tools:
                    response = await provider.generate_with_tools(
                        messages=messages,
                        tools=tools,
                        temperature=temperature,
                        max_tokens=max_tokens,
                        **kwargs,
                    )
                else:
                    response = await provider.generate(
                        messages=messages,
                        temperature=temperature,
                        max_tokens=max_tokens,
                        **kwargs,
                    )

                latency_ms = round((time.monotonic() - start_time) * 1000, 2)
                logger.info(
                    "LLM call succeeded",
                    provider=provider.name,
                    model=provider.model,
                    latency_ms=latency_ms,
                    tokens_total=response.usage.total_tokens,
                )

                # Write to cache
                if self.enable_cache and cache_key:
                    await self.cache.set(cache_key, response)

                return response

            except Exception as e:
                latency_ms = round((time.monotonic() - start_time) * 1000, 2)
                logger.warning(
                    "LLM provider failed, falling back to next provider",
                    provider=provider.name,
                    error=str(e),
                    latency_ms=latency_ms,
                )
                last_error = e
                continue

        raise RuntimeError(
            f"All configured LLM providers failed or are unavailable. Last error: {last_error}"
        )
