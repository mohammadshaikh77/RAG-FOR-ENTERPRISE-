"""Redis-based rate limiting middleware.

Enforces per-user and per-IP request quotas using atomic Redis sliding windows.
Returns HTTP 429 with 'Retry-After' header and friendly message when exceeded.
"""

import time
from collections.abc import Callable
from typing import Any

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from apps.api.src.config import get_settings
from apps.api.src.db.redis import get_redis_client
from apps.api.src.logging import get_logger

logger = get_logger("cite.middleware.ratelimit")
settings = get_settings()

EXCLUDED_PATHS = {
    "/health",
    "/healthz",
    "/metrics",
    "/docs",
    "/redoc",
    "/openapi.json",
    "/favicon.ico",
}


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Enforces per-IP and per-user request limits with Redis."""

    def __init__(
        self,
        app: Any,
        requests_per_minute: int = 120,
        user_requests_per_minute: int = 60,
    ) -> None:
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
        self.user_requests_per_minute = user_requests_per_minute

    async def dispatch(self, request: Request, call_next: Callable[..., Any]) -> Response:
        path = request.url.path

        # Bypass rate limiting for documentation, health checks, and metrics
        if path in EXCLUDED_PATHS or path.startswith("/docs") or path.startswith("/eval"):
            return await call_next(request)  # type: ignore[no-any-return]

        # Extract client IP
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            client_ip = forwarded_for.split(",")[0].strip()
        elif request.client:
            client_ip = request.client.host
        else:
            client_ip = "127.0.0.1"

        # Extract User ID from Authorization header if present
        auth_header = request.headers.get("Authorization", "")
        user_id_key: str | None = None
        if auth_header.startswith("Bearer "):
            # Use hashed token snippet as user identifier key
            token = auth_header.split(" ")[1]
            if len(token) > 16:
                user_id_key = f"rl:user:{token[:16]}"

        try:
            redis = get_redis_client()
            current_minute = int(time.time() // 60)

            # 1. Check IP limit
            ip_key = f"rl:ip:{client_ip}:{current_minute}"
            pipe = redis.pipeline()
            pipe.incr(ip_key)
            pipe.expire(ip_key, 60)

            # 2. Check User limit if authenticated
            if user_id_key:
                u_key = f"{user_id_key}:{current_minute}"
                pipe.incr(u_key)
                pipe.expire(u_key, 60)

            results = await pipe.execute()
            ip_count = results[0]

            if ip_count > self.requests_per_minute:
                retry_after = 60 - int(time.time() % 60)
                logger.warning("Rate limit exceeded for IP", client_ip=client_ip, count=ip_count)
                return JSONResponse(
                    status_code=429,
                    content={
                        "detail": f"Too many requests, try again in {retry_after} seconds",
                        "retry_after": retry_after,
                    },
                    headers={"Retry-After": str(retry_after)},
                )

            if user_id_key and len(results) >= 3:
                user_count = results[2]
                if user_count > self.user_requests_per_minute:
                    retry_after = 60 - int(time.time() % 60)
                    logger.warning(
                        "Rate limit exceeded for User", user_key=user_id_key, count=user_count
                    )
                    return JSONResponse(
                        status_code=429,
                        content={
                            "detail": f"Too many requests, try again in {retry_after} seconds",
                            "retry_after": retry_after,
                        },
                        headers={"Retry-After": str(retry_after)},
                    )

        except Exception as e:
            # Fallback gracefully if Redis is temporarily unreachable
            logger.warning("Rate limiter bypassed due to Redis error", error=str(e))

        return await call_next(request)  # type: ignore[no-any-return]
