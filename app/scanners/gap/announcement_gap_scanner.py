"""Announcement gap scanner for multi-condition filtering."""

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import TYPE_CHECKING

from loguru import logger
from vnpy.trader.constant import Exchange, Interval

from app.external.vnpy.database import get_database_manager
from app.scanners.base import ScannerBase, ScanResult
from app.scanners.gap.filters import PriceVolumeFilter
from app.scanners.gap.gap_detector import GapDetector
from app.scanners.gap.opening_range import OpeningRangeTracker

if TYPE_CHECKING:
    from app.external.vnpy.database import DatabaseManager

__all__ = ["AnnouncementGapScanner", "AnnouncementGapCandidate"]


register_announcement: Callable[[str, datetime], None] | None = None

try:
    from app.strategies.announcement_gap_strategy import (
        register_announcement as _ra,
    )

    register_announcement = _ra
except ImportError:
    pass


@dataclass
class AnnouncementGapCandidate:
    """Candidate passing all announcement gap strategy conditions."""

    symbol: str
    gap_pct: float
    six_month_high: float
    current_price: float
    announcement_headline: str
    announcement_time: datetime
    exchange: Exchange = Exchange.LOCAL


class AnnouncementGapScanner(ScannerBase):
    """Scanner for announcement gap breakout candidates.

    Filters stocks by:
    1. Made announcement today
    2. Positive gap
    3. Price > 6-month high
    4. Price > minimum threshold
    """

    def __init__(self, db_manager: "DatabaseManager | None" = None) -> None:
        """Initialize announcement gap scanner.

        Args:
            db_manager: Database manager instance (optional, will create if None)
        """
        self.db_manager = db_manager or get_database_manager()
        self.gap_detector = GapDetector(self.db_manager)
        self.price_volume_filter = PriceVolumeFilter(self.db_manager)
        self.or_tracker = OpeningRangeTracker(self.db_manager)

    @property
    def name(self) -> str:
        """Scanner identifier."""
        return "announcement_gap_scanner"

    async def execute(self) -> ScanResult:
        """Execute the scan operation.

        Returns:
            ScanResult with results or error details
        """
        candidates = await self.scan_candidates(
            announcement_symbols=[],
            min_price=0.20,
            min_gap_pct=0.0,
            lookback_months=6,
        )

        return ScanResult(
            success=True,
            message=f"Found {len(candidates)} announcement gap candidates",
            data=[c.__dict__ for c in candidates],
            error=None,
        )

    async def scan_candidates(
        self,
        announcement_symbols: list[tuple[str, str, datetime]],
        min_price: float = 0.20,
        min_gap_pct: float = 0.0,
        lookback_months: int = 6,
    ) -> list[AnnouncementGapCandidate]:
        """Scan for announcement gap breakout candidates.

        Args:
            announcement_symbols: List of (symbol, headline, time) tuples
            min_price: Minimum stock price threshold
            min_gap_pct: Minimum gap percentage
            lookback_months: Lookback period for high calculation

        Returns:
            List of candidates passing all filters
        """
        logger.info(
            f"Scanning {len(announcement_symbols)} announcement symbols with filters: "
            f"price>=${min_price:.2f}, gap>={min_gap_pct}%, 6M high, lookback={lookback_months}M"
        )

        candidates = []

        for symbol, headline, ann_time in announcement_symbols:
            try:
                candidate = await self._evaluate_symbol(
                    symbol, headline, ann_time, min_price, min_gap_pct, lookback_months
                )

                if candidate:
                    candidates.append(candidate)
                    if register_announcement is not None:
                        register_announcement(symbol, ann_time)
                    logger.info(
                        f"✓ Candidate found: {symbol} gap={candidate.gap_pct:.2f}% "
                        f"price=${candidate.current_price:.2f} > 6M ${candidate.six_month_high:.2f}"
                    )

            except Exception as e:
                logger.error(f"Error evaluating {symbol}: {e}")

        logger.info(f"Found {len(candidates)} candidates passing all filters")

        return candidates

    async def _evaluate_symbol(
        self,
        symbol: str,
        headline: str,
        ann_time: datetime,
        min_price: float,
        min_gap_pct: float,
        lookback_months: int,
    ) -> AnnouncementGapCandidate | None:
        """Evaluate a single symbol against all criteria.

        Args:
            symbol: Stock symbol
            headline: Announcement headline
            ann_time: Announcement timestamp
            min_price: Minimum price threshold
            min_gap_pct: Minimum gap percentage
            lookback_months: Lookback period in months

        Returns:
            AnnouncementGapCandidate if passes all filters, None otherwise
        """
        bars = self.db_manager.load_bars(
            symbol=symbol,
            exchange=Exchange.LOCAL,
            interval=Interval.DAILY,
        )

        if not bars or len(bars) < 2:
            logger.debug(f"✗ {symbol}: Insufficient bar data")
            return None

        latest_bar = bars[-1]
        previous_bar = bars[-2]

        if latest_bar.close_price < min_price:
            logger.debug(f"✗ {symbol}: Price ${latest_bar.close_price:.2f} < ${min_price:.2f}")
            return None

        gap_pct = (
            (latest_bar.open_price - previous_bar.close_price) / previous_bar.close_price * 100
        )

        if gap_pct < min_gap_pct:
            logger.debug(f"✗ {symbol}: Gap {gap_pct:.2f}% < {min_gap_pct}%")
            return None

        six_month_high = self._calculate_six_month_high(bars, lookback_months)

        if latest_bar.close_price <= six_month_high:
            logger.debug(
                f"✗ {symbol}: Price ${latest_bar.close_price:.2f} <= 6M ${six_month_high:.2f}"
            )
            return None

        return AnnouncementGapCandidate(
            symbol=symbol,
            gap_pct=gap_pct,
            six_month_high=six_month_high,
            current_price=latest_bar.close_price,
            announcement_headline=headline,
            announcement_time=ann_time,
            exchange=Exchange.LOCAL,
        )

    def _calculate_six_month_high(self, bars: list, lookback_months: int = 6) -> float:
        """Calculate N-month high from bar data.

        Args:
            bars: List of bar data
            lookback_months: Lookback period in months

        Returns:
            N-month high price
        """
        cutoff_days = lookback_months * 30
        cutoff_date = datetime.now() - timedelta(days=cutoff_days)

        if not bars:
            return 0.0

        relevant_bars = [b for b in bars if b.datetime >= cutoff_date]

        if not relevant_bars:
            return bars[-1].high_price

        return max(b.high_price for b in relevant_bars)

    async def sample_opening_ranges(
        self, candidates: list[AnnouncementGapCandidate]
    ) -> dict[str, float]:
        """Sample opening range high for candidates.

        Args:
            candidates: List of announcement gap candidates

        Returns:
            Dictionary of symbol → opening range high
        """
        symbols = [c.symbol for c in candidates]

        logger.info(f"Sampling opening ranges for {len(symbols)} candidates")

        or_dict = await self.or_tracker.sample_opening_range(symbols)

        result = {symbol: data.orh for symbol, data in or_dict.items()}

        return result
