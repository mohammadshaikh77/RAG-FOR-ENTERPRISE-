"""Token-bucket rate limiter to prevent hitting free-tier 429 rate limits."""

import asyncio
import time

import structlog

logger = structlog.get_logger(__name__)


class TokenBucketLimiter:
    """Asynchronous token-bucket rate limiter.

    Ensures outbound requests do not exceed the configured requests-per-minute (RPM).
    """

    def __init__(self, requests_per_minute: int, name: str = "default") -> None:
        self.name = name
        self.capacity = float(max(1, requests_per_minute))
        self.tokens = self.capacity
        self.fill_rate = self.capacity / 60.0  # tokens per second
        self.last_update = time.monotonic()
        self._lock = asyncio.Lock()

    async def acquire(self, tokens: float = 1.0) -> None:
        """Acquires a token, asynchronously waiting if the rate limit is currently exhausted."""
        async with self._lock:
            now = time.monotonic()
            elapsed = now - self.last_update
            self.last_update = now

            # Replenish tokens based on elapsed time
            self.tokens = min(self.capacity, self.tokens + elapsed * self.fill_rate)

            if self.tokens < tokens:
                needed = tokens - self.tokens
                wait_time = needed / self.fill_rate
                logger.info(
                    "Rate limit reached, pausing",
                    limiter=self.name,
                    wait_seconds=round(wait_time, 2),
                )
                await asyncio.sleep(wait_time)
                self.tokens = 0.0
                self.last_update = time.monotonic()
            else:
                self.tokens -= tokens
