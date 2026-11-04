from fastapi import APIRouter, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from apps.api.src.config import get_settings
from apps.api.src.db.redis import check_redis_health
from apps.api.src.db.session import check_database_health

router = APIRouter(tags=["Health"])
settings = get_settings()


class ComponentStatus(BaseModel):
    database: str
    redis: str


class HealthResponse(BaseModel):
    status: str
    version: str
    environment: str
    components: ComponentStatus


@router.get("/health", response_model=HealthResponse)
async def health_check() -> JSONResponse:
    """Comprehensive health check returning component statuses."""
    db_ok = await check_database_health()
    redis_ok = await check_redis_health()

    components = ComponentStatus(
        database="connected" if db_ok else "disconnected",
        redis="connected" if redis_ok else "disconnected",
    )

    is_healthy = db_ok and redis_ok
    overall_status = "healthy" if is_healthy else "degraded"
    http_status = status.HTTP_200_OK if (db_ok or redis_ok) else status.HTTP_503_SERVICE_UNAVAILABLE

    return JSONResponse(
        status_code=http_status,
        content={
            "status": overall_status,
            "version": settings.app_version,
            "environment": settings.environment,
            "components": components.model_dump(),
        },
    )
