"""Unit tests for Phase 7 Redis-based rate limiting middleware."""

import pytest
from fastapi import FastAPI
from fastapi.responses import PlainTextResponse
from httpx import ASGITransport, AsyncClient

from apps.api.src.middleware.rate_limit import RateLimitMiddleware


@pytest.fixture
def test_app() -> FastAPI:
    app = FastAPI()
    # Configure tight limits for testing: 3 requests/min
    app.add_middleware(RateLimitMiddleware, requests_per_minute=3, user_requests_per_minute=2)

    @app.get("/test-endpoint")
    async def sample_endpoint() -> PlainTextResponse:
        return PlainTextResponse("OK")

    @app.get("/health")
    async def health_endpoint() -> PlainTextResponse:
        return PlainTextResponse("HEALTHY")

    return app


@pytest.mark.asyncio
async def test_rate_limiting_enforcement_and_retry_after(test_app: FastAPI) -> None:
    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # First 3 requests succeed
        for i in range(3):
            resp = await client.get("/test-endpoint", headers={"X-Forwarded-For": "198.51.100.42"})
            assert resp.status_code == 200, f"Request {i + 1} failed"

        # 4th request exceeds rate limit of 3
        resp_blocked = await client.get(
            "/test-endpoint", headers={"X-Forwarded-For": "198.51.100.42"}
        )
        assert resp_blocked.status_code == 429
        assert "Retry-After" in resp_blocked.headers
        data = resp_blocked.json()
        assert "Too many requests, try again in" in data["detail"]
        assert "retry_after" in data


@pytest.mark.asyncio
async def test_rate_limiting_bypasses_health(test_app: FastAPI) -> None:
    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Excluded health path should never be rate limited
        for _ in range(10):
            resp = await client.get("/health", headers={"X-Forwarded-For": "198.51.100.42"})
            assert resp.status_code == 200
