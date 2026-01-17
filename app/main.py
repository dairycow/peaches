"""Main application entry point with orchestration and health checks."""

import asyncio
import sys
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager, suppress
from pathlib import Path

from fastapi import FastAPI
from loguru import logger
from vnpy.event import EventEngine
from vnpy.trader.engine import MainEngine
from vnpy_ctastrategy import CtaEngine

from app.config import config
from app.gateway import gateway_manager
from app.health import health_checker
from app.health import router as health_router
from app.import_api import router as import_router
from app.scheduler import get_scheduler
from app.strategies import DEFAULT_PARAMETERS, STRATEGY_NAME, VT_SYMBOL

cta_engine: CtaEngine | None = None
scheduler = get_scheduler()


def initialize_cta_engine(main_engine: MainEngine, event_engine: EventEngine) -> CtaEngine:
    """Initialize CTA strategy engine.

    Args:
        main_engine: Main trading engine
        event_engine: Event engine

    Returns:
        CtaEngine instance
    """
    global cta_engine
    cta_engine = CtaEngine(main_engine, event_engine)
    cta_engine.init_engine()

    cta_engine.add_strategy(
        "ASXMomentumStrategy",
        STRATEGY_NAME,
        VT_SYMBOL,
        DEFAULT_PARAMETERS,
    )

    return cta_engine


app = FastAPI(
    title="vnpy-trading-bot",
    description="Production-ready headless trading bot for vn.py",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Application lifespan manager.

    Args:
        app: FastAPI instance

    Yields:
        None
    """
    await startup()

    yield

    await shutdown()


app.include_router(health_router)
app.include_router(import_router)


_health_check_task: asyncio.Task[None] | None = None


async def startup() -> None:
    """Initialize application components."""
    logger.info("Starting vnpy-trading-bot...")

    _setup_logging()

    try:
        await _initialize_gateway()
        await _initialize_strategies()
        if config.historical_data.import_enabled:
            await scheduler.start()
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


async def _initialize_gateway() -> None:
    """Initialize IB Gateway connection."""
    logger.info("Initializing IB Gateway connection...")

    try:
        await gateway_manager.start()
        health_checker.set_gateway_status(True)
        logger.info("IB Gateway connection established")
    except Exception as e:
        health_checker.set_gateway_status(False)
        logger.error(f"Failed to initialize IB Gateway: {e}")
        raise


async def _initialize_strategies() -> None:
    """Initialize trading strategies."""
    logger.info("Initializing strategies...")

    try:
        connection = gateway_manager.get_connection()
        if not connection or not connection.main_engine or not connection.event_engine:
            raise RuntimeError("Gateway connection not available")

        global cta_engine
        cta_engine = initialize_cta_engine(connection.main_engine, connection.event_engine)
        cta_engine.init_all_strategies()
        cta_engine.start_all_strategies()

        logger.info("Strategies initialized and started")

    except Exception as e:
        logger.error(f"Failed to initialize strategies: {e}")
        raise


def _start_health_checks() -> None:
    """Start health check monitoring."""
    global _health_check_task

    if not config.health.enabled:
        logger.info("Health checks disabled")
        return

    logger.info("Health checks enabled")
    _health_check_task = asyncio.create_task(_health_check_loop())


async def _health_check_loop() -> None:
    """Run periodic health checks."""
    while True:
        try:
            connection = gateway_manager.get_connection()

            if connection and connection.is_connected():
                health_checker.set_gateway_status(True)
            else:
                health_checker.set_gateway_status(False)
                if config.gateway.auto_reconnect:
                    logger.warning("Gateway disconnected, attempting to reconnect...")
                    try:
                        await gateway_manager.start()
                    except Exception as e:
                        logger.error(f"Reconnection failed: {e}")

            await asyncio.sleep(config.health.interval_seconds)

        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"Health check error: {e}")
            await asyncio.sleep(config.health.interval_seconds)


async def shutdown() -> None:
    """Gracefully shutdown application."""
    global _health_check_task

    logger.info("Shutting down application...")

    try:
        if _health_check_task is not None:
            _health_check_task.cancel()
            with suppress(asyncio.CancelledError):
                await _health_check_task

        if cta_engine is not None:
            cta_engine.stop_all_strategies()

        if scheduler.is_running():
            await scheduler.stop()

        await gateway_manager.stop()
        logger.info("Application shutdown complete")

    except Exception as e:
        logger.error(f"Error during shutdown: {e}")


async def cleanup() -> None:
    """Cleanup resources."""
    logger.info("Cleaning up resources...")

    try:
        await gateway_manager.stop()
    except Exception as e:
        logger.error(f"Cleanup error: {e}")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8080,
        log_config=None,
        access_log=False,
    )
