"""Price and volume filters for scanner."""

from typing import TYPE_CHECKING

from loguru import logger
from vnpy.trader.constant import Exchange, Interval

from app.database import get_database_manager

if TYPE_CHECKING:
    pass


class PriceVolumeFilter:
    """Filter stocks by price and volume criteria."""

    def __init__(self, db_manager) -> None:
        """Initialize price/volume filter.

        Args:
            db_manager: Database manager instance
        """
        self.db_manager = db_manager

    async def filter_by_price(self, symbols: list[str], min_price: float = 1.0) -> list[str]:
        """Filter symbols by minimum price.

        Args:
            symbols: List of symbol strings
            min_price: Minimum stock price

        Returns:
            Filtered list of symbols
        """
        filtered = []

        for symbol in symbols:
            bars = self.db_manager.load_bars(
                symbol=symbol,
                exchange=Exchange.LOCAL,
                interval=Interval.DAILY,
            )

            if bars:
                latest_price = bars[-1].close_price

                if latest_price >= min_price:
                    filtered.append(symbol)
                    logger.debug(
                        f"✓ {symbol} passes price filter: ${latest_price:.2f} >= ${min_price:.2f}"
                    )
                else:
                    logger.debug(
                        f"✗ {symbol} fails price filter: ${latest_price:.2f} < ${min_price:.2f}"
                    )

        logger.info(f"Price filter: {len(symbols)} → {len(filtered)} symbols")
        return filtered

    async def filter_by_volume(self, symbols: list[str], min_volume: int = 100000) -> list[str]:
        """Filter symbols by minimum volume.

        Args:
            symbols: List of symbol strings
            min_volume: Minimum daily volume

        Returns:
            Filtered list of symbols
        """
        filtered = []

        for symbol in symbols:
            bars = self.db_manager.load_bars(
                symbol=symbol,
                exchange=Exchange.LOCAL,
                interval=Interval.DAILY,
            )

            if bars:
                latest_volume = bars[-1].volume

                if latest_volume >= min_volume:
                    filtered.append(symbol)
                    logger.debug(
                        f"✓ {symbol} passes volume filter: {latest_volume:,} >= {min_volume:,}"
                    )
                else:
                    logger.debug(
                        f"✗ {symbol} fails volume filter: {latest_volume:,} < {min_volume:,}"
                    )

        logger.info(f"Volume filter: {len(symbols)} → {len(filtered)} symbols")
        return filtered

    async def apply_filters(
        self, symbols: list[str], min_price: float = 1.0, min_volume: int = 100000
    ) -> list[str]:
        """Apply both price and volume filters.

        Args:
            symbols: List of symbol strings
            min_price: Minimum stock price
            min_volume: Minimum daily volume

        Returns:
            Filtered list of symbols
        """
        logger.info(
            f"Applying filters to {len(symbols)} symbols: price >= ${min_price}, volume >= {min_volume:,}"
        )

        filtered = await self.filter_by_price(symbols, min_price)
        filtered = await self.filter_by_volume(filtered, min_volume)

        return filtered
