"""Scheduled job manager for announcement scanning."""

import asyncio
from collections.abc import Awaitable, Callable
from typing import TYPE_CHECKING, TypedDict

if TYPE_CHECKING:
    pass

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from loguru import logger

from app.config import config


class JobResult(TypedDict):
    """Job execution result for tracking scan operations."""

    success: bool
    announcements_count: int
    processed_count: int
    error: str | None


class ScannerScheduler:
    """Scheduler for announcement scanning."""

    def __init__(self, scan_schedule: str) -> None:
        """Initialize scanner scheduler.

        Args:
            scan_schedule: Cron expression for scan
        """
        self.scheduler = AsyncIOScheduler(timezone="Australia/Sydney")
        self.scan_schedule = scan_schedule
        self._running = False
        self._lock = asyncio.Lock()

    def add_jobs(self, scan_func: "Callable[[], Awaitable[JobResult]]") -> None:
        """Add scheduled scan job.

        Args:
            scan_func: Async function to call for scan
        """
        self.scheduler.add_job(
            scan_func,
            trigger=CronTrigger.from_crontab(self.scan_schedule, timezone="Australia/Sydney"),
            id="asx_scan",
            name="Scan ASX price-sensitive announcements",
            replace_existing=True,
        )

        logger.info(f"Scheduled scan: {self.scan_schedule} (AEST)")

    async def start(self) -> None:
        """Start scanner scheduler."""
        async with self._lock:
            if self._running:
                logger.warning("Scanner scheduler already running")
                return

            self.scheduler.start()
            self._running = True
            logger.info("Scanner scheduler started")

    async def stop(self) -> None:
        """Stop scanner scheduler."""
        async with self._lock:
            if not self._running:
                return

            self.scheduler.shutdown(wait=True)
            self._running = False
            logger.info("Scanner scheduler stopped")

    def is_running(self) -> bool:
        """Check if scheduler is running.

        Returns:
            True if running, False otherwise
        """
        return self._running


async def run_scan() -> JobResult:
    """Run announcement scan job.

    Returns:
        Job result dictionary
    """
    logger.info("Running ASX announcement scan job")

    try:
        from app.scanners.asx import ASXPriceSensitiveScanner, ScannerConfig
        from app.services.notification_service import NotificationService
        from app.services.scanner_service import ScannerService
        from app.services.strategy_trigger_service import StrategyTriggerService

        scanner = ASXPriceSensitiveScanner(
            ScannerConfig(
                url=config.scanners.asx.url,
                timeout=config.scanners.asx.timeout,
            )
        )

        notification_service = NotificationService(
            webhook_url=config.scanners.notifications.discord.webhook_url,
            username=config.scanners.notifications.discord.username,
            enabled=config.scanners.notifications.discord.enabled,
        )

        strategy_trigger_service = StrategyTriggerService(
            enabled=config.scanners.triggers.enabled,
            strategy_names=config.scanners.triggers.strategies,
        )

        scanner_service = ScannerService(
            scanner=scanner,
            notification_service=notification_service,
            strategy_trigger_service=strategy_trigger_service,
        )

        result = await scanner_service.scan()
        logger.info(f"Scan job completed: {result}")
        return JobResult(
            success=result.get("success", False),
            announcements_count=result.get("announcements_count", 0),
            processed_count=result.get("processed_count", 0),
            error=result.get("error"),
        )

    except Exception as e:
        logger.error(f"Scan job failed: {e}")
        return JobResult(
            success=False,
            announcements_count=0,
            processed_count=0,
            error=str(e),
        )


scanner_scheduler: ScannerScheduler | None = None


def get_scanner_scheduler() -> ScannerScheduler:
    """Get or create scanner scheduler singleton.

    Returns:
        ScannerScheduler instance
    """
    global scanner_scheduler
    if scanner_scheduler is None:
        scanner_scheduler = ScannerScheduler(scan_schedule=config.scanners.asx.scan_schedule)
        scanner_scheduler.add_jobs(run_scan)
    return scanner_scheduler


async def reset_scanner_scheduler() -> None:
    """Reset scanner scheduler singleton for test isolation.

    Stops scanner scheduler if running and sets to None.
    """
    global scanner_scheduler
    if scanner_scheduler is not None and scanner_scheduler.is_running():
        await scanner_scheduler.stop()
    scanner_scheduler = None
