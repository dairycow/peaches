"""Gap detection scanner for identifying significant price gaps."""

from datetime import datetime

import polars as pl

from app.analysis.stock_data import StockData


class GapScanner:
    """Scans for significant price gaps."""

    def __init__(self, stocks: dict[str, StockData]):
        """Initialize GapScanner.

        Args:
            stocks: Dictionary of ticker -> StockData
        """
        self.stocks = stocks

    def find_gaps(
        self,
        start_date: datetime,
        end_date: datetime,
        gap_threshold: float = 10.0,
        volume_multiplier: float = 2.0,
        min_volume: int = 50000,
    ) -> list[dict]:
        """Find gaps over a period.

        Args:
            start_date: Start date for scanning
            end_date: End date for scanning
            gap_threshold: Minimum gap percentage (default 10%)
            volume_multiplier: Minimum volume multiple vs 50-day avg (default 2x)
            min_volume: Minimum daily volume (default 50k)

        Returns:
            List of gap dictionaries with details
        """
        gaps: list[dict] = []

        for _ticker, stock in self.stocks.items():
            stock_gaps = self._find_gaps_in_stock(
                stock,
                start_date,
                end_date,
                gap_threshold,
                volume_multiplier,
                min_volume,
            )
            gaps.extend(stock_gaps)

        gaps.sort(key=lambda x: x["gap_percent"], reverse=True)
        return gaps

    def _find_gaps_in_stock(
        self,
        stock: StockData,
        start_date: datetime,
        end_date: datetime,
        gap_threshold: float,
        volume_multiplier: float,
        min_volume: int,
    ) -> list[dict]:
        """Find gaps in a single stock.

        Args:
            stock: StockData object
            start_date: Start date
            end_date: End date
            gap_threshold: Minimum gap percentage
            volume_multiplier: Volume multiple threshold
            min_volume: Minimum daily volume

        Returns:
            List of gap dictionaries
        """
        gaps: list[dict] = []

        if stock.df is None or stock.df.is_empty():
            return gaps

        period_df = stock.filter_by_date_range(start_date, end_date)

        if period_df.is_empty() or len(period_df) < 2:
            return gaps

        for i in range(1, len(period_df)):
            current = period_df.row(i, named=True)
            previous = period_df.row(i - 1, named=True)

            gap = ((current["open"] - previous["close"]) / previous["close"]) * 100

            if gap >= gap_threshold:
                filtered_df = stock.df.filter(pl.col("date") < current["date"])
                if len(filtered_df) >= 50:
                    volume_mean = filtered_df["volume"].tail(50).mean()
                    avg_volume = (
                        float(volume_mean)
                        if volume_mean is not None and isinstance(volume_mean, (int, float))
                        else 0.0
                    )
                else:
                    avg_volume = 0.0

                vol_multiple = current["volume"] / avg_volume if avg_volume > 0 else 0

                if current["volume"] >= min_volume and vol_multiple >= volume_multiplier:
                    gaps.append(
                        {
                            "ticker": stock.ticker,
                            "date": current["date"].isoformat(),
                            "gap_percent": gap,
                            "open": float(current["open"]),
                            "prev_close": float(previous["close"]),
                            "high": float(current["high"]),
                            "low": float(current["low"]),
                            "close": float(current["close"]),
                            "volume": int(current["volume"]),
                            "avg_volume_50d": int(avg_volume),
                            "volume_multiple": vol_multiple,
                        }
                    )

        return gaps
