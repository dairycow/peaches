"""Opening range tracker."""

from datetime import datetime
from typing import TYPE_CHECKING

from loguru import logger
from vnpy.trader.constant import Exchange, Interval
from vnpy.trader.object import BarData

from app.database import get_database_manager

if TYPE_CHECKING:
    pass


class OpeningRangeTracker:
    """Track opening ranges for gap candidates."""

    def __init__(self, db_manager) -> None:
        """Initialize opening range tracker.

        Args:
            db_manager: Database manager instance
        """
        self.db_manager = db_manager
        self._or_cache: dict[str, OpeningRange] = {}

    async def sample_opening_range(
        self, symbols: list[str], sample_time: datetime | None = None
    ) -> dict[str, OpeningRange]:
        """Sample opening range for multiple symbols at a specific time.

        Args:
            symbols: List of symbol strings
            sample_time: Time to sample (defaults to 10:05 AM AEDT)

        Returns:
            Dictionary of symbol → opening range
        """
        if sample_time is None:
            sample_time = self._get_default_sample_time()

        logger.info(f"Sampling opening ranges for {len(symbols)} symbols at {sample_time}")

        result = {}

        for symbol in symbols:
            try:
                bars = self.db_manager.load_bars(
                    symbol=symbol,
                    exchange=Exchange.LOCAL,
                    interval=Interval.DAILY,
                )

                if bars:
                    or_result = await self._calculate_or_from_bars(bars, sample_time)
                    result[symbol] = or_result
                    logger.debug(
                        f"✓ {symbol} OR: ${or_result.orh:.2f} / ${or_result.orl:.2f} @ ${or_result.price:.2f}"
                    )

            except Exception as e:
                logger.error(f"Error sampling OR for {symbol}: {e}")

        self._or_cache = result
        logger.info(f"Sampled opening range for {len(result)} symbols")

        return result

    async def get_opening_range(self, symbol: str) -> OpeningRange | None:
        """Get cached opening range for a symbol.

        Args:
            symbol: Stock symbol

        Returns:
            Opening range or None
        """
        return self._or_cache.get(symbol)

    def _get_default_sample_time(self) -> datetime:
        """Get default opening range sample time (10:05 AM AEDT).

        Returns:
            Default sample time datetime
        """
        now = datetime.now()
        return now.replace(hour=10, minute=5, second=0, microsecond=0)

    async def _calculate_or_from_bars(
        self, bars: list[BarData], sample_time: datetime
    ) -> OpeningRange:
        """Calculate opening range from bar data at specific time.

        Args:
            bars: List of bar data
            sample_time: Time to sample opening range

        Returns:
            Opening range result
        """
        target_bar = None

        for bar in bars:
            if bar.datetime == sample_time:
                target_bar = bar
                break

        if not target_bar:
            logger.warning(f"No bar found at {sample_time}, using latest bar")
            target_bar = bars[-1]

        orh = max(target_bar.high_price, target_bar.open_price)
        orl = min(target_bar.low_price, target_bar.open_price)

        return OpeningRange(
            symbol=target_bar.symbol,
            orh=orh,
            orl=orl,
            price=target_bar.open_price,
            sample_time=target_bar.datetime,
        )
