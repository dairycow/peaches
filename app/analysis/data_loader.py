"""Data loading utilities for backtesting."""

from datetime import datetime
from typing import TYPE_CHECKING

from vnpy.trader.constant import Exchange, Interval

if TYPE_CHECKING:
    from vnpy.trader.object import BarData

from app.database import get_database_manager


def load_bars(
    symbol: str,
    start: datetime,
    end: datetime,
    exchange: Exchange = Exchange.LOCAL,
    interval: Interval = Interval.DAILY,
) -> list["BarData"]:
    """Load OHLCV bar data from database.

    Args:
        symbol: Trading symbol (e.g., "BHP")
        start: Start datetime
        end: End datetime
        exchange: Exchange (default: LOCAL for CSV data)
        interval: Bar interval (default: DAILY)

    Returns:
        List of BarData objects
    """
    db = get_database_manager()
    return db.load_bars(symbol, exchange, interval, start, end)


def list_available_symbols() -> list[str]:
    """Get list of available symbols in database.

    Returns:
        List of symbol names
    """
    db = get_database_manager()
    overview = db.get_overview()
    return [o.symbol for o in overview if o.interval == Interval.DAILY]


def get_symbol_data_range(symbol: str) -> dict[str, str | int] | None:
    """Get available date range for a symbol.

    Args:
        symbol: Trading symbol

    Returns:
        Dict with 'start' and 'end' dates, or None if not found
    """
    db = get_database_manager()
    overview = db.get_overview()

    for o in overview:
        if (
            o.symbol == symbol
            and o.interval == Interval.DAILY
            and o.start is not None
            and o.end is not None
        ):
            return {
                "start": o.start.strftime("%Y-%m-%d"),
                "end": o.end.strftime("%Y-%m-%d"),
                "count": o.count,
            }
    return None


def load_bars_batch(
    symbols: list[str],
    start: datetime,
    end: datetime,
    exchange: Exchange = Exchange.LOCAL,
    interval: Interval = Interval.DAILY,
) -> dict[str, list["BarData"]]:
    """Load OHLCV bar data from database for multiple symbols.

    Args:
        symbols: List of trading symbols
        start: Start datetime
        end: End datetime
        exchange: Exchange (default: LOCAL for CSV data)
        interval: Bar interval (default: DAILY)

    Returns:
        Dictionary of symbol -> list of BarData objects
    """
    db = get_database_manager()
    result: dict[str, list["BarData"]] = {}

    for symbol in symbols:
        result[symbol] = db.load_bars(symbol, exchange, interval, start, end)

    return result
