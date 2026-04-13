"""Unified scheduler service."""

import asyncio
from typing import TYPE_CHECKING

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from loguru import logger

from app.config import config

if TYPE_CHECKING:
    from app.events.bus import EventBus


class SchedulerService:
    """Unified scheduler for all scheduled operations."""

    def __init__(self, event_bus: "EventBus") -> None:
        """Initialize scheduler service.

        Args:
            event_bus: EventBus instance
        """
        self.event_bus = event_bus
        self.scheduler = AsyncIOScheduler(timezone="Australia/Sydney")
        self._running = False
        self._lock = asyncio.Lock()

    async def _trigger_scan(self) -> None:
        """Trigger scan event."""
        from app.events.events import ScanStartedEvent

        await self.event_bus.publish(
            ScanStartedEvent(source="scheduled", correlation_id="scan_cron")
        )

    async def _trigger_download(self) -> None:
        """Trigger download event."""
        from app.events.events import DownloadStartedEvent

        await self.event_bus.publish(
            DownloadStartedEvent(
                source="scheduled",
                correlation_id="download_cron",
                target_date=None,
            )
        )

    async def _trigger_import(self) -> None:
        """Trigger import event."""
        from app.events.events import ImportStartedEvent

        await self.event_bus.publish(
            ImportStartedEvent(source="scheduled", correlation_id="import_cron")
        )

    async def _trigger_announcement_gap_scan(self) -> None:
        """Trigger announcement gap scan event."""
        from app.events.events import AnnouncementGapScanStartedEvent

        await self.event_bus.publish(
            AnnouncementGapScanStartedEvent(
                source="scheduled", correlation_id="announcement_gap_cron"
            )
        )

    async def initialize(self) -> None:
        """Register all scheduled jobs."""

        self.scheduler.add_job(
            self._trigger_scan,
            trigger=CronTrigger.from_crontab(
                config.scanners.asx.scan_schedule, timezone="Australia/Sydney"
            ),
            id="scan_trigger",
            name="Trigger ASX scan",
            replace_existing=True,
        )

        self.scheduler.add_job(
            self._trigger_download,
            trigger=CronTrigger.from_crontab(
                config.cooltrader.download_schedule, timezone="Australia/Sydney"
            ),
            id="download_trigger",
            name="Trigger download",
            replace_existing=True,
        )

        self.scheduler.add_job(
            self._trigger_import,
            trigger=CronTrigger.from_crontab(
                config.cooltrader.import_schedule, timezone="Australia/Sydney"
            ),
            id="import_trigger",
            name="Trigger import",
            replace_existing=True,
        )

        self.scheduler.add_job(
            self._trigger_announcement_gap_scan,
            trigger=CronTrigger.from_crontab(
                config.scanners.asx.announcement_gap_schedule, timezone="Australia/Sydney"
            ),
            id="announcement_gap_trigger",
            name="Trigger announcement gap scan",
            replace_existing=True,
        )

        logger.info(
            f"Scheduler initialized: scan={config.scanners.asx.scan_schedule}, "
            f"download={config.cooltrader.download_schedule}, "
            f"import={config.cooltrader.import_schedule}, "
            f"announcement_gap={config.scanners.asx.announcement_gap_schedule}"
        )

    async def start(self) -> None:
        """Start scheduler."""
        async with self._lock:
            if self._running:
                logger.warning("Scheduler already running")
                return

            self.scheduler.start()
            self._running = True
            logger.info("Scheduler started")

    async def stop(self) -> None:
        """Stop scheduler."""
        async with self._lock:
            if not self._running:
                return

            self.scheduler.shutdown(wait=True)
            self._running = False
            logger.info("Scheduler stopped")

    def is_running(self) -> bool:
        """Check if scheduler is running.

        Returns:
            True if running, False otherwise
        """
        return self._running


scheduler_service: SchedulerService | None = None


async def get_scheduler_service(event_bus: "EventBus") -> SchedulerService:
    """Get or create scheduler service singleton.

    Args:
        event_bus: EventBus instance

    Returns:
        SchedulerService instance
    """
    global scheduler_service
    if scheduler_service is None:
        scheduler_service = SchedulerService(event_bus)
        await scheduler_service.initialize()
    return scheduler_service


async def reset_scheduler_service() -> None:
    """Reset scheduler service singleton for test isolation."""
    global scheduler_service
    if scheduler_service is not None and scheduler_service.is_running():
        await scheduler_service.stop()
    scheduler_service = None
