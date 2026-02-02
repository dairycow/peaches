"""Discord notification handler."""

from loguru import logger

from app.events.bus import EventBus
from app.events.events import AnnouncementFoundEvent, ScanCompletedEvent
from app.services.notification_service import NotificationService


class DiscordHandler:
    """Handler for Discord notifications."""

    def __init__(self, notification_service: NotificationService) -> None:
        """Initialize Discord handler.

        Args:
            notification_service: Notification service instance
        """
        self.notification_service = notification_service

    async def initialize(self, event_bus: EventBus) -> None:
        """Subscribe to announcement events.

        Args:
            event_bus: EventBus instance
        """
        await event_bus.subscribe(AnnouncementFoundEvent, self.on_announcement)
        await event_bus.subscribe(ScanCompletedEvent, self.on_scan_complete)
        logger.info("DiscordHandler initialized")

    async def on_announcement(self, event: AnnouncementFoundEvent) -> None:
        """Handle announcement found event.

        Args:
            event: Announcement found event
        """
        logger.debug(f"DiscordHandler: Processing announcement for {event.ticker}")

        try:
            await self.notification_service.send_discord_webhook(
                ticker=event.ticker,
                headline=event.headline,
                timestamp=f"{event.date} {event.time}",
            )
        except Exception as e:
            logger.error(
                f"DiscordHandler failed to send notification for {event.ticker}: {e}",
                exc_info=True,
            )

    async def on_scan_complete(self, event: ScanCompletedEvent) -> None:
        """Handle scan completed event.

        Args:
            event: Scan completed event
        """
        if event.success:
            logger.info(f"Scan complete: {event.processed_count} announcements processed")
        else:
            logger.error(f"Scan failed: {event.error}")
