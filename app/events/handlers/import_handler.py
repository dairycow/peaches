"""Data import handler."""

from datetime import date

from loguru import logger

from app.events.bus import EventBus
from app.events.events import (
    DownloadCompletedEvent,
    DownloadStartedEvent,
    ImportCompletedEvent,
    ImportStartedEvent,
)
from app.external.cooltrader import create_downloader, create_importer


class ImportHandler:
    """Handler for data download and import operations."""

    def __init__(self, csv_dir: str) -> None:
        """Initialize import handler.

        Args:
            csv_dir: Directory for CSV files
        """
        self.csv_dir = csv_dir

    async def initialize(self, event_bus: EventBus) -> None:
        """Subscribe to import events.

        Args:
            event_bus: EventBus instance
        """
        self.event_bus = event_bus
        await event_bus.subscribe(DownloadStartedEvent, self.on_download_started)
        await event_bus.subscribe(ImportStartedEvent, self.on_import_started)
        logger.info("ImportHandler initialized")

    async def on_download_started(self, event: DownloadStartedEvent) -> None:
        """Handle download started event.

        Args:
            event: Download started event
        """
        logger.info(f"ImportHandler: Starting download for {event.target_date or 'yesterday'}")

        try:
            downloader = create_downloader()

            target_date = None
            if event.target_date:
                target_date = date.fromisoformat(event.target_date)
                filepath = await downloader.download_csv(target_date)
            else:
                filepath = await downloader.download_yesterday()

            await downloader.close()

            status = "success" if filepath else "skipped"
            reason = None if filepath else "no file available"

            await self.event_bus.publish(
                DownloadCompletedEvent(
                    source=event.source,
                    correlation_id=event.correlation_id,
                    filepath=str(filepath) if filepath else None,
                    status=status,
                    reason=reason,
                )
            )

        except Exception as e:
            logger.error(f"ImportHandler download failed: {e}", exc_info=True)
            await self.event_bus.publish(
                DownloadCompletedEvent(
                    source=event.source,
                    correlation_id=event.correlation_id,
                    filepath=None,
                    status="error",
                    reason=str(e),
                )
            )

    async def on_import_started(self, event: ImportStartedEvent) -> None:
        """Handle import started event.

        Args:
            event: Import started event
        """
        logger.info("ImportHandler: Starting CSV import")

        try:
            importer = create_importer(self.csv_dir)
            result = importer.import_all()

            await self.event_bus.publish(
                ImportCompletedEvent(
                    source=event.source,
                    correlation_id=event.correlation_id,
                    total_bars=result.get("total_bars_imported"),
                    success=result.get("success"),
                    errors=result.get("errors"),
                    skipped=result.get("skipped"),
                    total_files=result.get("total_files"),
                    status="success",
                )
            )

        except Exception as e:
            logger.error(f"ImportHandler import failed: {e}", exc_info=True)
            await self.event_bus.publish(
                ImportCompletedEvent(
                    source=event.source,
                    correlation_id=event.correlation_id,
                    total_bars=None,
                    success=None,
                    errors=None,
                    skipped=None,
                    total_files=None,
                    status="error",
                )
            )
