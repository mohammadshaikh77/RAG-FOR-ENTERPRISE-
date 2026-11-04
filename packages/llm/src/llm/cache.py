"""LLM response cache with in-memory and optional Redis persistence."""

import hashlib
import json
from typing import Any

import structlog
from redis.asyncio import Redis

from llm.types import ChatMessage, LLMResponse, ToolDefinition

logger = structlog.get_logger(__name__)


def generate_cache_key(
    provider: str,
    model: str,
    messages: list[ChatMessage],
    tools: list[ToolDefinition] | None = None,
    temperature: float = 0.0,
) -> str:
    """Computes a deterministic SHA-256 hash for identical queries."""
    payload = {
        "provider": provider,
        "model": model,
        "temperature": temperature,
        "messages": [m.to_api_dict() for m in messages],
        "tools": [t.to_api_dict() for t in tools] if tools else [],
    }
    dumped = json.dumps(payload, sort_keys=True, default=str)
    return f"llm_cache:{hashlib.sha256(dumped.encode('utf-8')).hexdigest()}"


class LLMCache:
    """Manages cached LLM responses in Redis and local memory."""

    def __init__(self, redis_client: Redis | None = None, ttl_seconds: int = 86400) -> None:
        self.redis = redis_client
        self.ttl_seconds = ttl_seconds
        self._memory_cache: dict[str, dict[str, Any]] = {}
        self._max_memory_entries = 1000

    async def get(self, key: str) -> LLMResponse | None:
        """Retrieves cached response from Redis or local memory."""
        # 1. Try local memory
        if key in self._memory_cache:
            data = self._memory_cache[key]
            return LLMResponse.model_validate(data)

        # 2. Try Redis if available
        if self.redis is not None:
            try:
                cached_bytes = await self.redis.get(key)
                if cached_bytes:
                    data = json.loads(cached_bytes)
                    self._memory_cache[key] = data
                    return LLMResponse.model_validate(data)
            except Exception as e:
                logger.warning("Failed to read from Redis cache", error=str(e))

        return None

    async def set(self, key: str, response: LLMResponse) -> None:
        """Stores LLM response in cache."""
        data = response.model_dump()
        # Keep memory cache size bounded
        if len(self._memory_cache) >= self._max_memory_entries:
            # Pop oldest key
            oldest_key = next(iter(self._memory_cache))
            self._memory_cache.pop(oldest_key, None)

        self._memory_cache[key] = data

        if self.redis is not None:
            try:
                serialized = json.dumps(data)
                await self.redis.set(key, serialized, ex=self.ttl_seconds)
            except Exception as e:
                logger.warning("Failed to write to Redis cache", error=str(e))
