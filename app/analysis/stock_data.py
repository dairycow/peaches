"""Data adapter for converting vn.py BarData to polars DataFrames."""

from datetime import datetime

import polars as pl

from vnpy.trader.object import BarData


def bars_to_dataframe(bars: list[BarData]) -> pl.DataFrame:
    """Convert vn.py BarData list to polars DataFrame.

    Args:
        bars: List of vn.py BarData objects

    Returns:
        Polars DataFrame with columns: date, open, high, low, close, volume
    """
    if not bars:
        return pl.DataFrame(
            schema={
                "date": pl.Date,
                "open": pl.Float64,
                "high": pl.Float64,
                "low": pl.Float64,
                "close": pl.Float64,
                "volume": pl.Int64,
            }
        )

    data = []
    for bar in bars:
        if bar.datetime is None:
            continue
        data.append(
            {
                "date": bar.datetime.date(),
                "open": bar.open_price,
                "high": bar.high_price,
                "low": bar.low_price,
                "close": bar.close_price,
                "volume": bar.volume,
            }
        )

    df = pl.DataFrame(data)
    return df.sort("date").unique(subset=["date"], maintain_order=True)


class StockData:
    """Stock data wrapper for pattern scanning."""

    def __init__(self, ticker: str, bars: list[BarData]):
        """Initialize StockData.

        Args:
            ticker: Stock symbol
            bars: List of vn.py BarData objects
        """
        self.ticker = ticker
        self.df = bars_to_dataframe(bars)

    def filter_by_date_range(self, start_date: datetime, end_date: datetime) -> pl.DataFrame:
        """Filter DataFrame by date range.

        Args:
            start_date: Start date
            end_date: End date

        Returns:
            Filtered DataFrame
        """
        if self.df is None or self.df.is_empty():
            return pl.DataFrame()

        return self.df.filter(
            (pl.col("date") >= start_date.date()) & (pl.col("date") <= end_date.date())
        )

    def get_close_prices(self) -> list[float]:
        """Get list of close prices.

        Returns:
            List of close prices
        """
        if self.df is None or self.df.is_empty():
            return []
        return self.df["close"].to_list()
