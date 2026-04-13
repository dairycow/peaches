"""Gap scanner orchestration for API endpoints."""

import asyncio
from datetime import datetime
from typing import TYPE_CHECKING

from loguru import logger

from app.analysis.types import Exchange, Interval
from app.external.database import get_database_manager
from app.scanners.gap.models import (
    GapCandidate,
    OpeningRange,
    ScanRequest,
    ScanResponse,
    ScanStatus,
)

if TYPE_CHECKING:
    from app.external.database import DatabaseManager


class GapScanner:
    """Main gap scanner orchestrator."""

    def __init__(self, db_manager: "DatabaseManager | None" = None) -> None:
        self.db_manager = db_manager or get_database_manager()
        self._status = ScanStatus(
            running=False,
            last_scan_time=None,
            last_scan_results=0,
        )
        self._scan_lock = asyncio.Lock()
        self._or_cache: dict[str, OpeningRange] = {}

    async def start_scan(self, request: ScanRequest) -> ScanResponse:
        """Start a gap scan with specified parameters."""
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
        """Execute the gap scan with filtering."""
        logger.info("Fetching historical bar data for gap detection")

        all_bars = self.db_manager.get_overview()

        if not all_bars:
            logger.warning("No bar data available for gap scanning")
            return []

        logger.info(f"Processing {len(all_bars)} symbols for gap detection")

        candidates: list[GapCandidate] = []

        for bar_overview in all_bars:
            bars = self.db_manager.load_bars(
                symbol=bar_overview.symbol,
                exchange=Exchange(bar_overview.exchange),
                interval=Interval(bar_overview.interval),
            )

            if not bars or len(bars) < 2:
                continue

            prev_close = bars[-2].close_price
            curr_open = bars[-1].open_price
            gap_percent = (curr_open - prev_close) / prev_close * 100

            if abs(gap_percent) >= request.gap_threshold:
                candidates.append(
                    GapCandidate(
                        symbol=bars[-1].symbol,
                        gap_percent=abs(gap_percent),
                        gap_direction="up" if gap_percent >= 0 else "down",
                        previous_close=prev_close,
                        open_price=curr_open,
                        volume=int(bars[-1].volume),
                        price=curr_open,
                        timestamp=bars[-1].datetime,
                    )
                )

        if request.min_price > 0 or request.min_volume > 0:
            filtered = []
            for c in candidates:
                bars = self.db_manager.load_bars(
                    symbol=c.symbol,
                    exchange=Exchange.LOCAL,
                    interval=Interval.DAILY,
                )
                if bars:
                    latest = bars[-1]
                    if (
                        latest.close_price >= request.min_price
                        and latest.volume >= request.min_volume
                    ):
                        filtered.append(c)
            candidates = filtered

        candidates = candidates[: request.max_results]
        logger.info(f"Final candidates: {len(candidates)}")
        return candidates

    async def get_candidates_for_date(self, date: datetime) -> list[GapCandidate]:
        """Get gap candidates for a specific date."""
        logger.info(f"Fetching gap candidates for {date}")

        all_bars = self.db_manager.get_overview()
        candidates: list[GapCandidate] = []

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
                            gap_percent=abs(gap_percent),
                            gap_direction="up" if gap_percent >= 0 else "down",
                            previous_close=prev_close,
                            open_price=curr_open,
                            volume=int(bars[i].volume),
                            price=curr_open,
                            timestamp=bars[i].datetime,
                        )
                    )

        logger.info(f"Found {len(candidates)} candidates for {date}")
        return candidates

    async def get_status(self) -> ScanStatus:
        """Get current scanner status."""
        return self._status

    async def sample_opening_ranges(self, symbols: list[str]) -> dict[str, OpeningRange]:
        """Sample opening range for multiple symbols."""
        logger.info(f"Sampling opening ranges for {len(symbols)} symbols")

        result: dict[str, OpeningRange] = {}

        for symbol in symbols:
            try:
                bars = self.db_manager.load_bars(
                    symbol=symbol,
                    exchange=Exchange.LOCAL,
                    interval=Interval.DAILY,
                )

                if bars:
                    target_bar = bars[-1]
                    orh = max(target_bar.high_price, target_bar.open_price)
                    orl = min(target_bar.low_price, target_bar.open_price)
                    result[symbol] = OpeningRange(
                        symbol=target_bar.symbol,
                        orh=orh,
                        orl=orl,
                        price=target_bar.open_price,
                        sample_time=target_bar.datetime,
                    )

            except Exception as e:
                logger.error(f"Error sampling OR for {symbol}: {e}")

        self._or_cache = result
        return result
