"""Scanner service for orchestrating announcement scanning."""

from typing import TYPE_CHECKING, Any

from loguru import logger

from app.scanners.base import ScannerBase

if TYPE_CHECKING:
    from app.events.bus import EventBus


class ScannerService:
    """Service for orchestrating announcement scanning."""

    def __init__(self, scanner: ScannerBase[Any], event_bus: "EventBus") -> None:
        """Initialize scanner service.

        Args:
            scanner: ScannerBase instance
            event_bus: EventBus instance
        """
        self.scanner = scanner
        self.event_bus = event_bus

    async def scan(self) -> None:
        """Run scanner and publish events."""
        try:
            logger.info("Starting announcement scan")

            from app.events.events import (
                AnnouncementFoundEvent,
                ScanCompletedEvent,
                ScanStartedEvent,
            )

            await self.event_bus.publish(
                ScanStartedEvent(source="manual", correlation_id="manual_scan")
            )

            result = await self.scanner.execute()

            if not result.success:
                logger.error(f"Scan failed: {result.error}")
                await self.event_bus.publish(
                    ScanCompletedEvent(
                        source="manual",
                        correlation_id="manual_scan",
                        total_announcements=0,
                        processed_count=0,
                        success=False,
                        error=result.error,
                    )
                )
                return

            if isinstance(result.data, list):
                announcements = [a for a in result.data if isinstance(a, dict)]
            else:
                announcements = []
            logger.info(f"Processing {len(announcements)} announcements")

            processed_count = 0

            for announcement in announcements:
                from datetime import datetime

                date_str = announcement.get("date", "")
                time_str = announcement.get("time", "")
                try:
                    timestamp = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")
                except ValueError:
                    timestamp = datetime.now()

                await self.event_bus.publish(
                    AnnouncementFoundEvent(
                        source="manual",
                        correlation_id="manual_scan",
                        ticker=announcement["ticker"],
                        headline=announcement["headline"],
                        date=announcement["date"],
                        time=announcement["time"],
                        timestamp=timestamp,
                    )
                )
                processed_count += 1

            await self.event_bus.publish(
                ScanCompletedEvent(
                    source="manual",
                    correlation_id="manual_scan",
                    total_announcements=len(announcements),
                    processed_count=processed_count,
                    success=True,
                    error=None,
                )
            )

            logger.info(f"Scan complete: processed {processed_count} announcements")

        except Exception as e:
            logger.error(f"Error during scan: {e}", exc_info=True)
            await self.event_bus.publish(
                ScanCompletedEvent(
                    source="manual",
                    correlation_id="manual_scan",
                    total_announcements=0,
                    processed_count=0,
                    success=False,
                    error=str(e),
                )
            )
