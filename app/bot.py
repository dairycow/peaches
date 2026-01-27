"""Trading bot application manager."""

import asyncio
from contextlib import suppress
from typing import TYPE_CHECKING

from loguru import logger

from app.scheduler import get_scanner_scheduler, get_scheduler
from app.services.gateway_service import gateway_service
from app.services.strategy_service import strategy_service

if TYPE_CHECKING:
    from app.events.bus import EventBus
    from app.scheduler.import_scheduler import ImportScheduler
    from app.scheduler.scanner_scheduler import ScannerScheduler


class TradingBot:
    """Trading bot application manager.

    Encapsulates bot lifecycle and state.
    """

    def __init__(self) -> None:
        """Initialize trading bot manager."""
        self.gateway_service = gateway_service
        self.strategy_service = strategy_service
        self.scheduler: ImportScheduler | None = None
        self.scanner_scheduler: ScannerScheduler | None = None
        self._health_check_task: asyncio.Task[None] | None = None
        self.event_bus: EventBus | None = None

    async def start(self) -> None:
        """Start the trading bot."""
        logger.info("Starting trading bot...")

        from app.api.v1.scanner import init_scanner

        try:
            from app.events.bus import EventBus

            self.event_bus = EventBus()
            await self.event_bus.start()
            logger.info("Event bus started")

            await self.gateway_service.start()

            try:
                await self.strategy_service.start()
            except Exception as e:
                logger.warning(f"Failed to initialize strategies: {e}")
                logger.info("Continuing without strategies")

            init_scanner()
            logger.info("Gap scanner initialized")

            self.scheduler = get_scheduler()
            from app.config import config

            if config.historical_data.import_enabled:
                await self.scheduler.start()

            self.scanner_scheduler = get_scanner_scheduler()
            if config.scanners.enabled:
                await self.scanner_scheduler.start()

            self._start_health_checks()
            logger.info("Trading bot started successfully")
        except Exception as e:
            logger.error(f"Failed to start trading bot: {e}")
            await self.stop()
            raise

    async def stop(self) -> None:
        """Stop the trading bot."""
        logger.info("Stopping trading bot...")

        try:
            if self._health_check_task is not None:
                self._health_check_task.cancel()
                with suppress(asyncio.CancelledError):
                    await self._health_check_task

            self.strategy_service.stop()

            if self.scheduler and self.scheduler.is_running():
                await self.scheduler.stop()

            if self.scanner_scheduler and self.scanner_scheduler.is_running():
                await self.scanner_scheduler.stop()

            if self.event_bus:
                await self.event_bus.stop()

            await self.gateway_service.stop()
            logger.info("Trading bot stopped successfully")
        except Exception as e:
            logger.error(f"Error stopping trading bot: {e}")

    def _start_health_checks(self) -> None:
        """Start health check monitoring."""
        from app.config import config

        if not config.health.enabled:
            logger.info("Health checks disabled")
            return

        logger.info("Health checks enabled")
        self._health_check_task = asyncio.create_task(self._run_health_checks())

    async def _run_health_checks(self) -> None:
        """Run periodic health checks."""
        await self.gateway_service.health_check_loop()


_bot: TradingBot | None = None


def get_bot() -> TradingBot:
    """Get trading bot instance.

    Returns:
        TradingBot singleton instance
    """
    global _bot
    if _bot is None:
        _bot = TradingBot()
    return _bot


def reset_bot() -> None:
    """Reset bot singleton (for testing)."""
    global _bot
    if _bot is not None:
        _bot = None
