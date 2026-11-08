import time
import uuid
from collections.abc import AsyncGenerator, Callable
from contextlib import asynccontextmanager
from typing import Any

import structlog
from cite_mcp.server import create_mcp_server
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware

from apps.api.src.config import get_settings
from apps.api.src.logging import get_logger, setup_logging
from apps.api.src.middleware.rate_limit import RateLimitMiddleware
from apps.api.src.routers.agent import router as agent_router
from apps.api.src.routers.auth import router as auth_router
from apps.api.src.routers.documents import router as documents_router
from apps.api.src.routers.eval import router as eval_router
from apps.api.src.routers.health import router as health_router
from apps.api.src.routers.retrieval import router as retrieval_router
from apps.api.src.routers.review_queue import router as review_queue_router

settings = get_settings()
setup_logging(log_level=settings.log_level, environment=settings.environment)
logger = get_logger("cite.api")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    logger.info(
        "Starting Cite API service",
        version=settings.app_version,
        environment=settings.environment,
        llm_providers=settings.llm_provider_order,
    )
    yield
    logger.info("Shutting down Cite API service")


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://rag-for-enterprise.vercel.app",
    ],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.middleware("http")
async def request_context_middleware(request: Request, call_next: Callable[..., Any]) -> Response:
    """Assigns unique request ID and logs duration."""
    request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
    structlog.contextvars.clear_contextvars()
    structlog.contextvars.bind_contextvars(
        request_id=request_id,
        path=request.url.path,
        method=request.method,
    )

    start_time = time.perf_counter()
    response: Response = await call_next(request)
    duration_ms = round((time.perf_counter() - start_time) * 1000, 2)

    response.headers["X-Request-ID"] = request_id
    response.headers["X-Response-Time-Ms"] = str(duration_ms)

    logger.info(
        "HTTP request completed",
        status_code=response.status_code,
        duration_ms=duration_ms,
    )
    return response


# Include routers
app.include_router(health_router)
app.include_router(auth_router)
app.include_router(documents_router)
app.include_router(retrieval_router)
app.include_router(agent_router)
app.include_router(review_queue_router)
app.include_router(eval_router)

# Rate limiting middleware
app.add_middleware(RateLimitMiddleware, requests_per_minute=120, user_requests_per_minute=60)

# Mount Model Context Protocol (MCP) SSE server
mcp_server = create_mcp_server()
app.mount("/mcp", mcp_server.sse_app())


@app.get("/")
async def root() -> dict[str, str]:
    return {
        "service": settings.app_name,
        "version": settings.app_version,
        "status": "running",
        "docs": "/docs",
    }
