"""Trading bot application manager."""

from typing import TYPE_CHECKING

from loguru import logger

from app.config import config
from app.events import get_event_bus, reset_event_bus
from app.events.handlers import (
    AnnouncementGapHandler,
    DiscordHandler,
    EventHandler,
    ImportHandler,
)
from app.scanners.asx import ScannerConfig
from app.services import (
    get_notification_service,
    get_scheduler_service,
    reset_scheduler_service,
)
from app.services.announcement_gap_strategy_service import AnnouncementGapStrategyService

if TYPE_CHECKING:
    from app.events.bus import EventBus
    from app.services.scheduler_service import SchedulerService


class TradingBot:
    """Trading bot application manager."""

    def __init__(self) -> None:
        """Initialize trading bot manager."""
        self.scheduler: SchedulerService | None = None
        self.event_bus: EventBus | None = None

    async def start(self) -> None:
        """Start the trading bot."""
        logger.info("Starting trading bot...")

        from app.api.v1.scanner import init_scanner

        try:
            self.event_bus = get_event_bus()
            await self.event_bus.start()
            logger.info("Event bus started")

            init_scanner()
            logger.info("Gap scanner initialized")

            notification_service = get_notification_service(
                webhook_url=config.scanners.notifications.discord.webhook_url,
                username=config.scanners.notifications.discord.username,
                enabled=config.scanners.notifications.discord.enabled,
            )

            asx_scanner_config = ScannerConfig(
                url=config.scanners.asx.url,
                timeout=config.scanners.asx.timeout,
            )

            announcement_gap_strategy_service = AnnouncementGapStrategyService(
                asx_scanner_config=asx_scanner_config,
                min_price=config.announcement_gap_strategy.min_price,
                min_gap_pct=config.announcement_gap_strategy.min_gap_pct,
                lookback_months=config.announcement_gap_strategy.lookback_months,
            )

            handlers: list[EventHandler] = [
                DiscordHandler(notification_service),
                ImportHandler(csv_dir=config.historical_data.csv_dir),
                AnnouncementGapHandler(
                    notification_service=notification_service,
                    strategy_service=announcement_gap_strategy_service,
                ),
            ]

            for handler in handlers:
                await handler.initialize(self.event_bus)

            logger.info(f"Event handlers initialized ({len(handlers)} handlers)")

            if config.historical_data.import_enabled or config.scanners.enabled:
                self.scheduler = await get_scheduler_service(self.event_bus)
                await self.scheduler.start()
                logger.info("Scheduler started")

            logger.info("Trading bot started successfully")

        except Exception as e:
            logger.error(f"Failed to start trading bot: {e}", exc_info=True)
            await self.stop()
            raise

    async def stop(self) -> None:
        """Stop the trading bot."""
        logger.info("Stopping trading bot...")

        try:
            if self.scheduler and self.scheduler.is_running():
                await self.scheduler.stop()

            if self.event_bus:
                await self.event_bus.stop()

            logger.info("Trading bot stopped successfully")

        except Exception as e:
            logger.error(f"Error stopping trading bot: {e}")


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
