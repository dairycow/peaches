"""Gap detector and opening range tracking."""

from datetime import datetime
from typing import NamedTuple

from loguru import logger
from vnpy.trader.constant import Exchange, Interval
from vnpy.trader.object import BarData


class OpeningRangeResult(NamedTuple):
    """Opening range result for a stock."""

    symbol: str
    orh: float
    orl: float
    price: float
    sample_time: datetime


class GapDetector:
    """Detect gaps in opening range."""

    def __init__(self, db_manager) -> None:
        """Initialize gap detector.

        Args:
            db_manager: Database manager instance
        """
        self.db_manager = db_manager

    async def detect_gaps_from_bars(
        self, bars: list[BarData], gap_threshold: float = 3.0
    ) -> list[OpeningRangeResult]:
        """Detect gaps from historical bar data.

        Args:
            bars: List of bar data
            gap_threshold: Minimum gap percentage

        Returns:
            List of opening range results with gaps
        """
        if not bars or len(bars) < 2:
            return []

        logger.info(f"Detecting gaps in {len(bars)} bars with threshold {gap_threshold}%")

        gaps = []

        for i in range(1, len(bars)):
            prev_close = bars[i - 1].close_price
            curr_open = bars[i].open_price

            gap_percent = (curr_open - prev_close) / prev_close * 100

            if abs(gap_percent) >= gap_threshold:
                orh = max(bars[i].high_price, curr_open)
                orl = min(bars[i].low_price, curr_open)

                gaps.append(
                    OpeningRangeResult(
                        symbol=bars[i].symbol,
                        orh=orh,
                        orl=orl,
                        price=curr_open,
                        sample_time=bars[i].datetime,
                    )
                )

                logger.info(
                    f"Detected gap: {bars[i].symbol} {gap_percent:+.2f}% "
                    f"(prev_close={prev_close:.2f}, open={curr_open:.2f})"
                )

        logger.info(f"Found {len(gaps)} gaps meeting threshold {gap_threshold}%")
        return gaps

    async def detect_gaps_from_db(
        self, symbol: str, gap_threshold: float = 3.0
    ) -> list[OpeningRangeResult]:
        """Detect gaps from database for a symbol.

        Args:
            symbol: Stock symbol
            gap_threshold: Minimum gap percentage

        Returns:
            List of opening range results with gaps
        """
        logger.info(f"Detecting gaps for {symbol} from database with threshold {gap_threshold}%")

        bars = self.db_manager.load_bars(
            symbol=symbol,
            exchange=Exchange.LOCAL,
            interval=Interval.DAILY,
        )

        return await self.detect_gaps_from_bars(bars, gap_threshold)

    async def calculate_opening_range_from_bars(
        self, bars: list[BarData], sample_time: datetime
    ) -> OpeningRangeResult:
        """Calculate opening range from bar data at specific time.

        Args:
            bars: List of bar data
            sample_time: Time to sample opening range

        Returns:
            Opening range result
        """
        if not bars:
            raise ValueError("No bar data provided")

        target_bar = None

        for bar in bars:
            if bar.datetime == sample_time:
                target_bar = bar
                break

        if not target_bar:
            target_bar = bars[-1]

        orh = target_bar.high_price
        orl = target_bar.low_price
        price = target_bar.open_price

        return OpeningRangeResult(
            symbol=target_bar.symbol,
            orh=orh,
            orl=orl,
            price=price,
            sample_time=target_bar.datetime,
        )
