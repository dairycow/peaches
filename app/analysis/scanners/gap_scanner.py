"""Gap detection scanner for identifying significant price gaps."""

import re
from datetime import datetime

import polars as pl

from app.analysis.stock_data import StockData

_OPTION_PREFIXES = (
    "KO",
    "LO",
    "WO",
    "IO",
    "SO",
    "JO",
    "MO",
    "NO",
    "PO",
    "TO",
    "UO",
    "VO",
    "XO",
    "YO",
    "ZO",
    "DO",
    "HO",
    "RO",
    "CO",
    "BO",
    "EO",
    "FO",
    "GO",
    "QO",
    "AO",
    "OO",
)

_COMPANY_OPTION_RE = re.compile(r"\d.*O[A-Z]?$")


def is_option_code(symbol: str) -> bool:
    """Check if an ASX symbol is an option, warrant, or structured product.

    Args:
        symbol: ASX ticker symbol

    Returns:
        True if the symbol appears to be an option/warrant code
    """
    if len(symbol) < 4:
        return False

    upper = symbol.upper()

    for prefix in _OPTION_PREFIXES:
        idx = upper.find(prefix)
        while idx >= 0:
            if idx >= 2 and idx + len(prefix) <= len(upper):
                return True
            idx = upper.find(prefix, idx + 1)

    return bool(_COMPANY_OPTION_RE.search(upper))


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
        direction: str = "up",
        sort_absolute: bool = False,
        min_price: float = 0.0,
        exclude_options: bool = False,
    ) -> list[dict]:
        """Find gaps over a period.

        Args:
            start_date: Start date for scanning
            end_date: End date for scanning
            gap_threshold: Minimum gap percentage (default 10%)
            volume_multiplier: Minimum volume multiple vs 50-day avg (default 2x).
                Set to 0 to disable volume filtering.
            min_volume: Minimum daily volume (default 50k). Set to 0 to disable.
            direction: Gap direction - "up", "down", or "both" (default "up")
            sort_absolute: Sort by absolute gap value instead of raw value (default False)
            min_price: Minimum previous close price (default 0.0). Set to 0 to disable.
            exclude_options: Exclude ASX option/warrant codes (default False)

        Returns:
            List of gap dictionaries with details
        """
        gaps: list[dict] = []

        for ticker, stock in self.stocks.items():
            if exclude_options and is_option_code(ticker):
                continue
            stock_gaps = self._find_gaps_in_stock(
                stock,
                start_date,
                end_date,
                gap_threshold,
                volume_multiplier,
                min_volume,
                direction,
                min_price=min_price,
            )
            gaps.extend(stock_gaps)

        if sort_absolute:
            gaps.sort(key=lambda x: abs(x["gap_percent"]), reverse=True)
        else:
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
        direction: str = "up",
        min_price: float = 0.0,
    ) -> list[dict]:
        """Find gaps in a single stock.

        Args:
            stock: StockData object
            start_date: Start date
            end_date: End date
            gap_threshold: Minimum gap percentage
            volume_multiplier: Volume multiple threshold (0 to disable)
            min_volume: Minimum daily volume (0 to disable)
            direction: Gap direction - "up", "down", or "both"
            min_price: Minimum previous close price (0 to disable)

        Returns:
            List of gap dictionaries
        """
        gaps: list[dict] = []

        if stock.df is None or stock.df.is_empty():
            return gaps

        period_df = stock.filter_by_date_range(start_date, end_date)

        if period_df.is_empty() or len(period_df) < 2:
            return gaps

        volume_filtering = volume_multiplier > 0 or min_volume > 0

        for i in range(1, len(period_df)):
            current = period_df.row(i, named=True)
            previous = period_df.row(i - 1, named=True)

            gap = ((current["open"] - previous["close"]) / previous["close"]) * 100
            gap_direction = "up" if gap >= 0 else "down"

            meets_direction = (
                (direction == "both")
                or (direction == "up" and gap >= gap_threshold)
                or (direction == "down" and gap <= -gap_threshold)
            )
            meets_threshold = abs(gap) >= gap_threshold if direction == "both" else True

            if not (meets_direction and meets_threshold):
                continue

            if min_price > 0 and previous["close"] < min_price:
                continue

            if volume_filtering:
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

                if current["volume"] < min_volume or vol_multiple < volume_multiplier:
                    continue
            else:
                avg_volume = 0.0
                vol_multiple = 0.0

            gaps.append(
                {
                    "ticker": stock.ticker,
                    "date": current["date"].isoformat(),
                    "gap_percent": gap,
                    "direction": gap_direction,
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
