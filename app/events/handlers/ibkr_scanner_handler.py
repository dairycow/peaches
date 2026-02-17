"""IBKR scanner event handler."""

from loguru import logger

from app.config import config
from app.events.events import IBKRGapFoundEvent, IBKRScanCompletedEvent, IBKRScanStartedEvent
from app.services.notification_service import get_notification_service


class IBKRScannerHandler:
    """Handles IBKR scanner events."""

    def __init__(self) -> None:
        """Initialize handler."""
        self.notification_service = get_notification_service(
            webhook_url=config.scanners.notifications.discord.webhook_url,
            username=config.scanners.notifications.discord.username,
            enabled=config.scanners.notifications.discord.enabled,
        )

    async def on_scan_started(self, event: IBKRScanStartedEvent) -> None:
        """Handle scan started event.

        Args:
            event: Scan started event
        """
        logger.info(f"IBKR scan started: {event.correlation_id}")

    async def on_gap_found(self, event: IBKRGapFoundEvent) -> None:
        """Handle gap found event - send Discord notifications.

        Args:
            event: Gap found event
        """
        if not event.gap_stocks:
            logger.info("No IBKR gaps found")
            return

        logger.info(f"IBKR gaps found: {len(event.gap_stocks)}")

        for gap_stock in event.gap_stocks:
            await self._send_discord_notification(gap_stock)

    async def on_scan_completed(self, event: IBKRScanCompletedEvent) -> None:
        """Handle scan completed event.

        Args:
            event: Scan completed event
        """
        if event.success:
            logger.info(f"IBKR scan completed successfully: {event.count} gaps found")
        else:
            logger.error(f"IBKR scan completed with error: {event.error}")

    async def _send_discord_notification(self, gap_stock) -> None:
        """Send Discord notification for a single gap stock.

        Args:
            gap_stock: GapStock object
        """
        headline = (
            f"Gap: +{gap_stock.gap_percent:.2f}%\n"
            f"Company: {gap_stock.company_name or 'N/A'}\n"
            f"Exchange: {gap_stock.exchange or 'N/A'}\n"
            f"Time: {gap_stock.timestamp.strftime('%H:%M:%S')}"
        )

        try:
            await self.notification_service.send_discord_webhook(
                ticker=gap_stock.ticker,
                headline=headline,
                timestamp=gap_stock.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
            )
        except Exception as e:
            logger.error(f"Failed to send Discord notification for {gap_stock.ticker}: {e}")
