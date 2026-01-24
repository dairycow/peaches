"""Main application entry point with orchestration and health checks."""

import asyncio
import sys
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager, suppress
from pathlib import Path
from typing import Any

from fastapi import FastAPI
from loguru import logger

from app.api.v1 import router as v1_router
from app.api.v1.scanner import init_scanner
from app.config import config
from app.scheduler import get_scanner_scheduler, get_scheduler
from app.services.gateway_service import gateway_service
from app.services.strategy_service import strategy_service

scheduler: Any = None
scanner_scheduler: Any = None

_health_check_task: asyncio.Task[None] | None = None


async def startup() -> None:
    """Initialize application components."""
    logger.info("Starting peaches-trading-bot...")

    from vnpy.trader.setting import SETTINGS
    import vnpy_sqlite.sqlite_database
    from vnpy.trader.utility import get_file_path

    SETTINGS["database.name"] = "sqlite"
    SETTINGS["database.database"] = config.database.path

    filename: str = SETTINGS["database.database"] or "database.db"
    path: str = str(get_file_path(filename))
    vnpy_sqlite.sqlite_database.db = vnpy_sqlite.sqlite_database.PeeweeSqliteDatabase(path)
    vnpy_sqlite.sqlite_database.path = path

    _setup_logging()

    global scheduler, scanner_scheduler
    scheduler = get_scheduler()
    scanner_scheduler = get_scanner_scheduler()

    try:
        await gateway_service.start()

        try:
            await strategy_service.start()
        except Exception as e:
            logger.warning(f"Failed to initialize strategies: {e}")
            logger.info("Continuing without strategies")

        init_scanner()
        logger.info("Gap scanner initialized")

        if config.historical_data.import_enabled:
            await scheduler.start()

        if config.scanners.enabled:
            await scanner_scheduler.start()

        _start_health_checks()
        logger.info("Application started successfully")
    except Exception as e:
        logger.error(f"Failed to start application: {e}")
        await cleanup()
        sys.exit(1)


def _setup_logging() -> None:
    """Configure logging."""
    log_level = config.logging.level
    logger.remove()

    if config.logging.json_format:
        logger.add(
            sys.stdout,
            level=log_level,
            format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} | {message}",
            serialize=True,
        )
    else:
        logger.add(
            sys.stdout,
            level=log_level,
            format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}:{function}:{line}</cyan> | <level>{message}</level>",
        )

    log_path = Path(config.logging.file)
    log_path.parent.mkdir(parents=True, exist_ok=True)

    logger.add(
        log_path,
        level=log_level,
        rotation=config.logging.rotation,
        retention=config.logging.retention,
        compression="zip",
        serialize=config.logging.json_format,
    )

    logger.info(f"Logging configured at {log_level} level")


def _start_health_checks() -> None:
    """Start health check monitoring."""
    global _health_check_task

    if not config.health.enabled:
        logger.info("Health checks disabled")
        return

    logger.info("Health checks enabled")
    _health_check_task = asyncio.create_task(_run_health_checks())


async def _run_health_checks() -> None:
    """Run periodic health checks."""
    await gateway_service.health_check_loop()


async def shutdown() -> None:
    """Gracefully shutdown application."""
    global _health_check_task

    logger.info("Shutting down application...")

    try:
        if _health_check_task is not None:
            _health_check_task.cancel()
            with suppress(asyncio.CancelledError):
                await _health_check_task

        strategy_service.stop()

        if scheduler.is_running():
            await scheduler.stop()

        if scanner_scheduler.is_running():
            await scanner_scheduler.stop()

        await gateway_service.stop()
        logger.info("Application shutdown complete")

    except Exception as e:
        logger.error(f"Error during shutdown: {e}")


async def cleanup() -> None:
    """Cleanup resources."""
    logger.info("Cleaning up resources...")

    try:
        await gateway_service.stop()
    except Exception as e:
        logger.error(f"Cleanup error: {e}")


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    """Application lifespan manager.

    Args:
        _app: FastAPI instance

    Yields:
        None
    """
    await startup()

    yield

    await shutdown()


app = FastAPI(
    title="peaches-trading-bot",
    description="Production-ready headless trading bot for vn.py",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

app.include_router(v1_router, prefix="/api/v1")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8080,
        log_config=None,
        access_log=False,
    )
