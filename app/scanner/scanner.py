"""Gap scanner orchestration."""

import asyncio
from datetime import datetime
from typing import TYPE_CHECKING

from loguru import logger
from vnpy.trader.constant import Exchange, Interval

from app.database import get_database_manager
from app.scanner.filters import PriceVolumeFilter
from app.scanner.gap_detector import GapDetector
from app.scanner.models import (
    GapCandidate,
    OpeningRange,
    ScanRequest,
    ScanResponse,
    ScanStatus,
)
from app.scanner.opening_range import OpeningRangeTracker

if TYPE_CHECKING:
    pass


class GapScanner:
    """Main gap scanner orchestrator."""

    def __init__(self, db_manager=None) -> None:
        """Initialize gap scanner.

        Args:
            db_manager: Database manager instance (optional, will create if None)
        """
        self.db_manager = db_manager or get_database_manager()
        self.gap_detector = GapDetector(self.db_manager)
        self.price_volume_filter = PriceVolumeFilter(self.db_manager)
        self.or_tracker = OpeningRangeTracker(self.db_manager)
        self._status = ScanStatus(
            running=False,
            last_scan_time=None,
            last_scan_results=0,
            active_scans=0,
        )
        self._scan_lock = asyncio.Lock()

    async def start_scan(self, request: ScanRequest) -> ScanResponse:
        """Start a gap scan with specified parameters.

        Args:
            request: Scan request with parameters

        Returns:
            Scan response with results
        """
        async with self._scan_lock:
            if self._status.running:
                logger.warning("Scan already in progress")
                return ScanResponse(
                    success=False,
                    scan_id="",
                    candidates_count=0,
                    estimated_completion=None,
                    message="Scan already in progress",
                )

            self._status.running = True
            self._status.last_scan_time = datetime.now()

            logger.info(f"Starting gap scan: {request}")
            scan_id = f"scan_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

            try:
                candidates = await self._execute_scan(request)
                self._status.last_scan_results = len(candidates)

                return ScanResponse(
                    success=True,
                    scan_id=scan_id,
                    candidates_count=len(candidates),
                    estimated_completion=None,
                    message=f"Scan completed. Found {len(candidates)} candidates",
                )

            except Exception as e:
                logger.error(f"Gap scan failed: {e}")
                return ScanResponse(
                    success=False,
                    scan_id=scan_id,
                    candidates_count=0,
                    estimated_completion=None,
                    message=f"Scan failed: {str(e)}",
                )
            finally:
                self._status.running = False

    async def _execute_scan(self, request: ScanRequest) -> list[GapCandidate]:
        """Execute the gap scan with filtering and opening range tracking.

        Args:
            request: Scan request parameters

        Returns:
            List of gap candidates meeting criteria
        """
        logger.info("Fetching historical bar data for gap detection")

        all_bars = self.db_manager.get_overview()

        if not all_bars:
            logger.warning("No bar data available for gap scanning")
            return []

        logger.info(f"Processing {len(all_bars)} symbols for gap detection")

        candidates = []

        for bar_overview in all_bars:
            bars = self.db_manager.load_bars(
                symbol=bar_overview.symbol,
                exchange=Exchange(bar_overview.exchange),
                interval=Interval(bar_overview.interval),
            )

            if not bars:
                continue

            detected_gaps = await self.gap_detector.detect_gaps_from_bars(
                bars, request.gap_threshold
            )

            for gap in detected_gaps:
                prev_close = bars[-2].close_price if len(bars) >= 2 else bars[0].open_price
                gap_percent = self._calculate_gap_percent(prev_close, gap.price)

                gap_candidate = GapCandidate(
                    symbol=gap.symbol,
                    gap_percent=gap_percent,
                    gap_direction="up" if gap_percent >= 0 else "down",
                    previous_close=prev_close,
                    open_price=gap.price,
                    volume=int(bars[-1].volume),
                    price=gap.price,
                    timestamp=gap.sample_time,
                    conid=0,
                )

                candidates.append(gap_candidate)

        logger.info(f"Detected {len(candidates)} raw gap candidates")

        if request.min_price > 0 or request.min_volume > 0:
            symbols = [c.symbol for c in candidates]
            filtered = await self.price_volume_filter.apply_filters(
                symbols, request.min_price, request.min_volume
            )

            candidates = [c for c in candidates if c.symbol in filtered]

        candidates = candidates[: request.max_results]

        logger.info(f"Final candidates: {len(candidates)}")

        return candidates

    async def wait_for_opening_range(
        self, candidates: list[GapCandidate]
    ) -> dict[str, OpeningRange]:
        """Wait for opening range sampling.

        Args:
            candidates: List of gap candidates

        Returns:
            Dictionary of symbol → opening range
        """
        symbols = [c.symbol for c in candidates]

        logger.info(f"Sampling opening range for {len(symbols)} candidates")

        return await self.or_tracker.sample_opening_range(symbols)

    def _calculate_gap_percent(self, prev_close: float, curr_open: float) -> float:
        """Calculate gap percentage.

        Args:
            prev_close: Previous day close price
            curr_open: Current day open price

        Returns:
            Gap percentage
        """
        return (curr_open - prev_close) / prev_close * 100

    async def get_status(self) -> ScanStatus:
        """Get current scanner status.

        Returns:
            Scanner status
        """
        return self._status

    async def get_candidates_for_date(self, date: datetime) -> list[GapCandidate]:
        """Get gap candidates for a specific date.

        Args:
            date: Date to query

        Returns:
            List of gap candidates
        """
        logger.info(f"Fetching gap candidates for {date}")

        all_bars = self.db_manager.get_overview()

        candidates = []

        for bar_overview in all_bars:
            bars = self.db_manager.load_bars(
                symbol=bar_overview.symbol,
                exchange=Exchange(bar_overview.exchange),
                interval=Interval(bar_overview.interval),
            )

            if not bars:
                continue

            for i in range(1, len(bars)):
                if bars[i].datetime.date() == date.date():
                    prev_close = bars[i - 1].close_price
                    curr_open = bars[i].open_price

                    gap_percent = (curr_open - prev_close) / prev_close * 100

                    candidates.append(
                        GapCandidate(
                            symbol=bars[i].symbol,
                            gap_percent=gap_percent,
                            gap_direction="up" if gap_percent >= 0 else "down",
                            previous_close=prev_close,
                            open_price=curr_open,
                            volume=int(bars[i].volume),
                            price=curr_open,
                            timestamp=bars[i].datetime,
                            conid=0,
                        )
                    )

            if not bars:
                continue

            for i in range(1, len(bars)):
                if bars[i].datetime.date() == date.date():
                    prev_close = bars[i - 1].close_price
                    curr_open = bars[i].open_price

                    gap_percent = (curr_open - prev_close) / prev_close * 100

                    candidates.append(
                        GapCandidate(
                            symbol=bars[i].symbol,
                            gap_percent=gap_percent,
                            gap_direction="up" if gap_percent >= 0 else "down",
                            previous_close=prev_close,
                            open_price=curr_open,
                            volume=int(bars[i].volume),
                            price=curr_open,
                            timestamp=bars[i].datetime,
                            conid=0,
                        )
                    )

        logger.info(f"Found {len(candidates)} candidates for {date}")
        return candidates
