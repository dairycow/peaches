"""Trading bot application manager."""

import asyncio
from contextlib import suppress
from typing import TYPE_CHECKING

from loguru import logger

from app.config import config
from app.events import get_event_bus, reset_event_bus
from app.events.handlers import (
    DiscordHandler,
    EventHandler,
    ImportHandler,
    StrategyHandler,
)
from app.scheduler import get_scheduler_service, reset_scheduler_service
from app.services import (
    get_notification_service,
    get_strategy_trigger_service,
)
from app.services.gateway_service import gateway_service
from app.services.strategy_service import strategy_service

if TYPE_CHECKING:
    from app.events.bus import EventBus
    from app.scheduler.scheduler_service import SchedulerService


class TradingBot:
    """Trading bot application manager."""

    def __init__(self) -> None:
        """Initialize trading bot manager."""
        self.gateway_service = gateway_service
        self.strategy_service = strategy_service
        self.scheduler: SchedulerService | None = None
        self.event_bus: EventBus | None = None
        self._health_check_task: asyncio.Task[None] | None = None

    async def start(self) -> None:
        """Start the trading bot."""
        logger.info("Starting trading bot...")

        from app.api.v1.scanner import init_scanner

        try:
            self.event_bus = get_event_bus()
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

            notification_service = get_notification_service(
                webhook_url=config.scanners.notifications.discord.webhook_url,
                username=config.scanners.notifications.discord.username,
                enabled=config.scanners.notifications.discord.enabled,
            )

            strategy_trigger_service = get_strategy_trigger_service(
                enabled=config.scanners.triggers.enabled,
                strategy_names=config.scanners.triggers.strategies,
            )

            handlers: list[EventHandler] = [
                DiscordHandler(notification_service),
                StrategyHandler(strategy_trigger_service),
                ImportHandler(csv_dir=config.historical_data.csv_dir),
            ]

            for handler in handlers:
                await handler.initialize(self.event_bus)

            logger.info(f"Event handlers initialized ({len(handlers)} handlers)")

            if config.historical_data.import_enabled or config.scanners.enabled:
                self.scheduler = await get_scheduler_service(self.event_bus)
                await self.scheduler.start()
                logger.info("Scheduler started")

            self._start_health_checks()
            logger.info("Trading bot started successfully")

        except Exception as e:
            logger.error(f"Failed to start trading bot: {e}", exc_info=True)
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

            if self.event_bus:
                await self.event_bus.stop()

            await self.gateway_service.stop()
            logger.info("Trading bot stopped successfully")

        except Exception as e:
            logger.error(f"Error stopping trading bot: {e}")

    def _start_health_checks(self) -> None:
        """Start health check monitoring."""
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


async def reset_bot() -> None:
    """Reset bot singleton (for testing)."""
    global _bot
    if _bot is not None:
        _bot = None
    await reset_scheduler_service()
    await reset_event_bus()
