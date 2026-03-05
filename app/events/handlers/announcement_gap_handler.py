"""Announcement gap scan event handler."""

from __future__ import annotations

from typing import TYPE_CHECKING

from loguru import logger

from app.events.events import AnnouncementGapScanCompletedEvent, AnnouncementGapScanStartedEvent
from app.scanners.gap.announcement_gap_scanner import AnnouncementGapCandidate
from app.services.announcement_gap_strategy_service import AnnouncementGapStrategyService
from app.services.notification_service import NotificationService

if TYPE_CHECKING:
    from app.events.bus import EventBus


class AnnouncementGapHandler:
    """Handles announcement gap scan events and sends Discord notifications."""

    def __init__(
        self,
        notification_service: NotificationService,
        strategy_service: AnnouncementGapStrategyService,
    ) -> None:
        """Initialize announcement gap handler.

        Args:
            notification_service: Notification service for Discord webhooks
            strategy_service: Service for running announcement gap scans
        """
        self.notification_service = notification_service
        self.strategy_service = strategy_service
        self.event_bus: EventBus | None = None

    async def initialize(self, event_bus: EventBus) -> None:
        """Subscribe to announcement gap scan events.

        Args:
            event_bus: EventBus instance
        """
        self.event_bus = event_bus
        await event_bus.subscribe(AnnouncementGapScanStartedEvent, self.on_scan_started)
        logger.info("AnnouncementGapHandler initialized")

    async def on_scan_started(self, event: AnnouncementGapScanStartedEvent) -> None:
        """Handle scan started event - run scan and send notifications.

        Args:
            event: Scan started event
        """
        logger.info(f"Announcement gap scan started: {event.correlation_id}")

        if not self.event_bus:
            logger.error("Event bus not initialised")
            return

        try:
            candidates = await self.strategy_service.run_daily_scan()

            for candidate in candidates:
                await self._send_discord_notification(candidate)

            await self._publish_completion(
                count=len(candidates),
                success=True,
                error=None,
            )

            logger.info(f"Announcement gap scan completed: {len(candidates)} candidates found")

        except Exception as e:
            logger.error(f"Announcement gap scan failed: {e}", exc_info=True)
            await self._publish_completion(
                count=0,
                success=False,
                error=str(e),
            )

    async def _send_discord_notification(self, candidate: AnnouncementGapCandidate) -> None:
        """Send Discord notification for a single candidate.

        Args:
            candidate: Announcement gap candidate
        """
        headline = self._truncate_headline(candidate.announcement_headline, 100)

        message = (
            f"**{candidate.symbol}**: +{candidate.gap_pct:.2f}% gap, "
            f"breaking 6M high (${candidate.six_month_high:.2f})\n"
            f"Announcement: {headline}\n"
            f"Price: ${candidate.current_price:.2f}"
        )

        timestamp = candidate.announcement_time.strftime("%Y-%m-%d %H:%M:%S")

        try:
            await self.notification_service.send_discord_webhook(
                ticker=candidate.symbol,
                headline=message,
                timestamp=timestamp,
            )
            logger.info(f"Discord notification sent for {candidate.symbol}")
        except Exception as e:
            logger.error(f"Failed to send Discord notification for {candidate.symbol}: {e}")

    def _truncate_headline(self, headline: str, max_len: int) -> str:
        """Truncate headline to max length with ellipsis.

        Args:
            headline: Original headline
            max_len: Maximum length

        Returns:
            Truncated headline
        """
        if len(headline) <= max_len:
            return headline
        return headline[: max_len - 3] + "..."

    async def _publish_completion(
        self,
        count: int,
        success: bool,
        error: str | None,
    ) -> None:
        """Publish scan completed event.

        Args:
            count: Number of candidates found
            success: Whether scan succeeded
            error: Error message if failed
        """
        if not self.event_bus:
            return

        await self.event_bus.publish(
            AnnouncementGapScanCompletedEvent(
                source="scheduled",
                correlation_id="announcement_gap_cron",
                count=count,
                success=success,
                error=error,
            )
        )
