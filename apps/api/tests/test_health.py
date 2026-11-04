from unittest.mock import patch

import pytest
from httpx import ASGITransport, AsyncClient

from apps.api.src.main import app


@pytest.mark.asyncio
async def test_root_endpoint() -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "running"
        assert "Cite" in data["service"]
        assert "X-Request-ID" in response.headers
        assert "X-Response-Time-Ms" in response.headers


@pytest.mark.asyncio
async def test_health_healthy() -> None:
    with (
        patch("apps.api.src.routers.health.check_database_health", return_value=True),
        patch("apps.api.src.routers.health.check_redis_health", return_value=True),
    ):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/health")
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "healthy"
            assert data["components"]["database"] == "connected"
            assert data["components"]["redis"] == "connected"


@pytest.mark.asyncio
async def test_health_degraded() -> None:
    with (
        patch("apps.api.src.routers.health.check_database_health", return_value=False),
        patch("apps.api.src.routers.health.check_redis_health", return_value=True),
    ):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/health")
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "degraded"
            assert data["components"]["database"] == "disconnected"
            assert data["components"]["redis"] == "connected"
