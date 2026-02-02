"""Strategy trigger handler."""

from loguru import logger

from app.events.bus import EventBus
from app.events.events import AnnouncementFoundEvent
from app.services.strategy_trigger_service import StrategyTriggerService


class StrategyHandler:
    """Handler for triggering strategies."""

    def __init__(self, strategy_trigger_service: StrategyTriggerService) -> None:
        """Initialize strategy handler.

        Args:
            strategy_trigger_service: Strategy trigger service instance
        """
        self.strategy_trigger_service = strategy_trigger_service

    async def initialize(self, event_bus: EventBus) -> None:
        """Subscribe to announcement events.

        Args:
            event_bus: EventBus instance
        """
        await event_bus.subscribe(AnnouncementFoundEvent, self.on_announcement)
        logger.info("StrategyHandler initialized")

    async def on_announcement(self, event: AnnouncementFoundEvent) -> None:
        """Handle announcement found event.

        Args:
            event: Announcement found event
        """
        logger.debug(f"StrategyHandler: Processing announcement for {event.ticker}")

        try:
            await self.strategy_trigger_service.trigger_strategies(
                ticker=event.ticker,
                headline=event.headline,
            )
        except Exception as e:
            logger.error(
                f"StrategyHandler failed to trigger strategies for {event.ticker}: {e}",
                exc_info=True,
            )
