from typing import Any

from arq.connections import RedisSettings

from apps.api.src.config import get_settings
from apps.api.src.logging import get_logger, setup_logging
from apps.worker.src.tasks import healthcheck_task, ingest_document_task

settings = get_settings()
setup_logging(log_level=settings.log_level, environment=settings.environment)
logger = get_logger("cite.worker")


async def startup(ctx: dict[str, Any]) -> None:
    logger.info("ARQ Worker process started", queue="cite-worker")


async def shutdown(ctx: dict[str, Any]) -> None:
    logger.info("ARQ Worker process stopping")


class WorkerSettings:
    """ARQ Worker configuration."""

    functions = [healthcheck_task, ingest_document_task]
    on_startup = startup
    on_shutdown = shutdown
    redis_settings = RedisSettings.from_dsn(settings.redis_url)
    max_jobs = 10
    poll_delay = 0.5


if __name__ == "__main__":
    from arq import run_worker

    run_worker(WorkerSettings)  # type: ignore[arg-type]
