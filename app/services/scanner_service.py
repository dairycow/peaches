"""Scanner service for orchestrating announcement scanning."""

from typing import TYPE_CHECKING

from loguru import logger

if TYPE_CHECKING:
    pass


class ScannerService:
    """Service for orchestrating announcement scanning."""

    def __init__(
        self,
        scanner,
        notification_service,
        strategy_trigger_service,
    ) -> None:
        """Initialize scanner service.

        Args:
            scanner: Announcement scanner instance
            notification_service: Notification service instance
            strategy_trigger_service: Strategy trigger service instance
        """
        self.scanner = scanner
        self.notification_service = notification_service
        self.strategy_trigger_service = strategy_trigger_service

    async def scan(self) -> dict:
        """Run scanner and process announcements.

        Returns:
            Scan results dictionary
        """
        try:
            logger.info("Starting announcement scan")

            result = await self.scanner.fetch_announcements()

            if not result.success:
                logger.error(f"Scan failed: {result.error}")
                return {
                    "success": False,
                    "announcements": [],
                    "error": result.error,
                }

            announcements = result.announcements
            logger.info(f"Processing {len(announcements)} announcements")

            processed_count = 0

            for announcement in announcements:
                await self._process_announcement(announcement)
                processed_count += 1

            logger.info(f"Scan complete: processed {processed_count} announcements")

            return {
                "success": True,
                "announcements_count": len(announcements),
                "processed_count": processed_count,
            }

        except Exception as e:
            logger.error(f"Error during scan: {e}")
            return {
                "success": False,
                "announcements": [],
                "error": str(e),
            }

    async def _process_announcement(self, announcement) -> None:
        """Process a single announcement.

        Args:
            announcement: Announcement object
        """
        ticker = announcement.ticker
        headline = announcement.headline

        try:
            await self.notification_service.send_discord_webhook(
                ticker=ticker,
                headline=headline,
                timestamp=announcement.timestamp,
            )
        except Exception as e:
            logger.error(f"Failed to notify for {ticker}: {e}")

        try:
            await self.strategy_trigger_service.trigger_strategies(
                ticker=ticker,
                headline=headline,
            )
        except Exception as e:
            logger.error(f"Failed to trigger strategy for {ticker}: {e}")


scanner_service: ScannerService | None = None


def get_scanner_service(
    scanner,
    notification_service,
    strategy_trigger_service,
) -> ScannerService:
    """Get or create scanner service singleton.

    Args:
        scanner: Scanner instance
        notification_service: Notification service instance
        strategy_trigger_service: Strategy trigger service instance

    Returns:
        ScannerService instance
    """
    global scanner_service
    if scanner_service is None:
        scanner_service = ScannerService(scanner, notification_service, strategy_trigger_service)
    return scanner_service
