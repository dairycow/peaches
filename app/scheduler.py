"""Scheduled job manager for automated data download and import."""

import asyncio
from collections.abc import Awaitable, Callable
from typing import TypedDict

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from loguru import logger

from app.config import config


class DownloadResult(TypedDict):
    status: str
    filepath: str | None
    reason: str | None


class ImportResult(TypedDict):
    status: str
    total_bars: int | None
    errors: int | None
    skipped: int | None
    success: int | None
    total_files: int | None
    reason: str | None


class ImportScheduler:
    """Scheduler for automated data downloads and imports."""

    def __init__(self, download_schedule: str, import_schedule: str) -> None:
        """Initialize scheduler.

        Args:
            download_schedule: Cron expression for download (e.g., "0 10 * * *")
            import_schedule: Cron expression for import (e.g., "5 10 * * *")
        """
        self.scheduler = AsyncIOScheduler(timezone="Australia/Sydney")
        self.download_schedule = download_schedule
        self.import_schedule = import_schedule
        self._running = False
        self._lock = asyncio.Lock()

    def add_jobs(
        self,
        download_func: "Callable[[], Awaitable[DownloadResult]]",
        import_func: "Callable[[], Awaitable[ImportResult]]",
    ) -> None:
        """Add scheduled download and import jobs.

        Args:
            download_func: Async function to call for download
            import_func: Async function to call for import
        """
        self.scheduler.add_job(
            download_func,
            trigger=CronTrigger.from_crontab(self.download_schedule, timezone="Australia/Sydney"),
            id="cooltrader_download",
            name="Download CSV from CoolTrader",
            replace_existing=True,
        )

        self.scheduler.add_job(
            import_func,
            trigger=CronTrigger.from_crontab(self.import_schedule, timezone="Australia/Sydney"),
            id="csv_import",
            name="Import CSVs to database",
            replace_existing=True,
        )

        logger.info(f"Scheduled download: {self.download_schedule} (AEST)")
        logger.info(f"Scheduled import: {self.import_schedule} (AEST)")

    async def start(self) -> None:
        """Start scheduler."""
        async with self._lock:
            if self._running:
                logger.warning("Scheduler already running")
                return

            self.scheduler.start()
            self._running = True
            logger.info("Import scheduler started")

    async def stop(self) -> None:
        """Stop scheduler."""
        async with self._lock:
            if not self._running:
                return

            self.scheduler.shutdown(wait=True)
            self._running = False
            logger.info("Import scheduler stopped")

    def is_running(self) -> bool:
        """Check if scheduler is running.

        Returns:
            True if running, False otherwise
        """
        return self._running


async def run_download() -> DownloadResult:
    """Run CoolTrader download job.

    Returns:
        Download result dictionary
    """
    logger.info("Running CoolTrader download job")

    try:
        from app.cooltrader import create_downloader

        downloader = create_downloader()
        filepath = await downloader.download_yesterday()
        await downloader.close()

        if filepath:
            logger.info(f"Download successful: {filepath}")
            return DownloadResult(status="success", filepath=str(filepath), reason=None)
        else:
            logger.warning("Download failed: No file available")
            return DownloadResult(status="skipped", filepath=None, reason="no file available")

    except Exception as e:
        logger.error(f"Download job failed: {e}")
        return DownloadResult(status="error", filepath=None, reason=str(e))


async def run_import() -> ImportResult:
    """Run CSV import job.

    Returns:
        Import summary dictionary
    """
    logger.info("Running CSV import job")

    try:
        from app.importer import create_importer

        importer = create_importer(config.historical_data.csv_dir)
        result = importer.import_all()
        logger.info(f"Import job completed: {result}")
        return ImportResult(
            status="success",
            total_bars=result.get("total_bars_imported"),
            errors=result.get("errors"),
            skipped=result.get("skipped"),
            success=result.get("success"),
            total_files=result.get("total_files"),
            reason=None,
        )
    except Exception as e:
        logger.error(f"Import job failed: {e}")
        return ImportResult(
            status="error",
            total_bars=None,
            errors=None,
            skipped=None,
            success=None,
            total_files=None,
            reason=str(e),
        )


scheduler: ImportScheduler | None = None


def get_scheduler() -> ImportScheduler:
    """Get or create scheduler singleton.

    Returns:
        ImportScheduler instance
    """
    global scheduler
    if scheduler is None:
        scheduler = ImportScheduler(
            download_schedule=config.cooltrader.download_schedule,
            import_schedule=config.cooltrader.import_schedule,
        )
        scheduler.add_jobs(run_download, run_import)
    return scheduler
