"""Main application entry point with orchestration and health checks."""

import sys
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from loguru import logger

from app.api.v1 import router as v1_router
from app.config import config


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


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    """Application lifespan manager.

    Args:
        _app: FastAPI instance

    Yields:
        None
    """
    from app.bot import get_bot
    from app.external.database import initialise_database

    logger.info("Starting peaches-trading-bot...")

    db_path = initialise_database()
    logger.info(f"Database initialised at {db_path}")

    _setup_logging()

    bot = get_bot()
    await bot.start()

    yield

    await bot.stop()


app = FastAPI(
    title="peaches-trading-bot",
    description="Trading bot for ASX announcements and gap scanning",
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
