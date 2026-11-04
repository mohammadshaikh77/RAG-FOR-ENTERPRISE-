import redis.asyncio as aioredis

from apps.api.src.config import get_settings
from apps.api.src.logging import get_logger

logger = get_logger("cite.redis")
settings = get_settings()

_redis_client: aioredis.Redis | None = None


def get_redis_client() -> aioredis.Redis:
    global _redis_client
    if _redis_client is None:
        _redis_client = aioredis.from_url(
            settings.redis_url,
            decode_responses=True,
            socket_timeout=2.0,
        )
    return _redis_client


async def check_redis_health() -> bool:
    """Checks if Redis is reachable."""
    try:
        client = get_redis_client()
        pong = await client.ping()
        return bool(pong)
    except Exception as e:
        logger.warning("Redis health check failed", error=str(e))
        return False
