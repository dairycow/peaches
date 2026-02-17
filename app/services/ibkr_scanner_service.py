"""IBKR scanner service for managing gap scans using ibind."""

from datetime import datetime
from typing import TYPE_CHECKING

from loguru import logger

from app.config import IBKRScannerConfig
from app.scanners.gap.ibkr_gap_scanner import IBKRGapScanner
from app.scanners.gap.models import GapStock

if TYPE_CHECKING:
    from app.events.bus import EventBus


class IBKRScannerService:
    """Service for managing IBKR gap scanner using ibind OAuth client."""

    def __init__(self, config: IBKRScannerConfig, event_bus: "EventBus") -> None:
        """Initialize IBKR scanner service.

        Args:
            config: IBKR scanner configuration
            event_bus: Event bus for publishing events
        """
        self.config = config
        self.event_bus = event_bus
        self._scanner: IBKRGapScanner | None = None
        self._running = False
        self._last_scan_time: datetime | None = None

    async def start(self) -> None:
        """Initialize IBKR scanner connection."""
        if self._running:
            logger.warning("IBKR scanner service already running")
            return

        if not self.config.enabled:
            logger.info("IBKR scanner is disabled in configuration")
            return

        logger.info("Starting IBKR scanner service...")

        try:
            self._scanner = IBKRGapScanner(self.config)
            self._scanner.connect()
            self._running = True
            logger.info("IBKR scanner service started")
        except Exception as e:
            logger.error(f"Failed to start IBKR scanner service: {e}")
            raise

    async def stop(self) -> None:
        """Disconnect IBKR scanner and cleanup."""
        if not self._running:
            return

        logger.info("Stopping IBKR scanner service...")

        if self._scanner:
            try:
                self._scanner.disconnect()
            except Exception as e:
                logger.warning(f"Error disconnecting scanner: {e}")

        self._running = False
        logger.info("IBKR scanner service stopped")

    async def scan_for_gaps(self, min_gap: float | None = None) -> list[GapStock]:
        """Execute gap scan and publish events.

        Args:
            min_gap: Minimum gap threshold (uses config default if None)

        Returns:
            List of GapStock objects
        """
        if not self._running or not self._scanner:
            raise RuntimeError("IBKR scanner service not running")

        if min_gap is None:
            min_gap = self.config.gap_threshold

        from app.events.events import (
            IBKRGapFoundEvent,
            IBKRScanCompletedEvent,
            IBKRScanStartedEvent,
        )

        correlation_id = f"ibkr_scan_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        await self.event_bus.publish(
            IBKRScanStartedEvent(source="scan", correlation_id=correlation_id)
        )

        logger.info(f"Starting IBKR gap scan (min_gap={min_gap}%)")

        try:
            original_threshold = self._scanner.config.gap_threshold
            if min_gap != original_threshold:
                self._scanner.config.gap_threshold = min_gap

            gap_stocks = self._scanner.scan_for_gaps()
            self._last_scan_time = datetime.now()

            if min_gap != original_threshold:
                self._scanner.config.gap_threshold = original_threshold

            logger.info(f"IBKR scan completed: {len(gap_stocks)} gaps found")

            await self.event_bus.publish(
                IBKRGapFoundEvent(
                    gap_stocks=gap_stocks,
                    source="scan",
                    correlation_id=correlation_id,
                )
            )

            await self.event_bus.publish(
                IBKRScanCompletedEvent(
                    count=len(gap_stocks),
                    success=True,
                    error=None,
                    source="scan",
                    correlation_id=correlation_id,
                )
            )

            return gap_stocks

        except Exception as e:
            logger.error(f"IBKR scan failed: {e}")
            await self.event_bus.publish(
                IBKRScanCompletedEvent(
                    count=0,
                    success=False,
                    error=str(e),
                    source="scan",
                    correlation_id=correlation_id,
                )
            )
            raise

    async def health_check(self) -> dict:
        """Check IBKR scanner health status.

        Returns:
            Health status dictionary
        """
        return {
            "enabled": self.config.enabled,
            "running": self._running,
            "connected": self._scanner.is_connected if self._scanner else False,
            "last_scan_time": self._last_scan_time.isoformat() if self._last_scan_time else None,
        }

    @property
    def last_scan_time(self) -> datetime | None:
        """Get last scan timestamp."""
        return self._last_scan_time

    @property
    def is_running(self) -> bool:
        """Check if service is running."""
        return self._running
