"""Data loading utilities for analysis."""

from datetime import datetime

import polars as pl
from loguru import logger

from app.analysis.types import BarData, Exchange, Interval
from app.config import config


def _get_db_path() -> str:
    from pathlib import Path

    configured = Path(config.database.path)
    if configured.exists():
        return str(configured)
    fallback = Path("data-prod/trading.db")
    if fallback.exists():
        return str(fallback.resolve())
    return str(configured)


def _query_df(query: str, params: list[str] | None = None) -> pl.DataFrame:
    import sqlite3

    db_path = _get_db_path()
    conn = sqlite3.connect(db_path)
    cur = conn.execute(query, params or [])
    cols = [d[0] for d in cur.description]
    rows = cur.fetchall()
    conn.close()

    if not rows:
        return pl.DataFrame(schema=cols)

    return pl.DataFrame(rows, schema=cols, orient="row")


def load_bars(
    symbol: str,
    start: datetime,
    end: datetime,
    exchange: Exchange = Exchange.LOCAL,
    interval: Interval = Interval.DAILY,
) -> list[BarData]:
    """Load OHLCV bar data from database.

    Args:
        symbol: Trading symbol (e.g., "BHP")
        start: Start datetime
        end: End datetime
        exchange: Exchange (default: LOCAL)
        interval: Bar interval (default: DAILY)

    Returns:
        List of BarData objects
    """
    start_str = start.strftime("%Y-%m-%d %H:%M:%S")
    end_str = end.strftime("%Y-%m-%d %H:%M:%S")

    df = _query_df(
        """
            SELECT symbol, exchange, interval, datetime,
                   open_price, high_price, low_price, close_price, volume
            FROM dbbardata
            WHERE symbol = ? AND interval = 'd' AND datetime >= ? AND datetime <= ?
            ORDER BY datetime
        """,
        [symbol, start_str, end_str],
    )

    bars: list[BarData] = []
    for row in df.iter_rows(named=True):
        bar = BarData(
            symbol=str(row["symbol"]),
            exchange=Exchange(str(row["exchange"])),
            interval=Interval(str(row["interval"])),
            datetime=_parse_datetime(row["datetime"]),
            open_price=float(row["open_price"]),
            high_price=float(row["high_price"]),
            low_price=float(row["low_price"]),
            close_price=float(row["close_price"]),
            volume=float(row["volume"]),
        )
        bars.append(bar)

    logger.info(f"Loaded {len(bars)} bars for {symbol}")
    return bars


def list_available_symbols() -> list[str]:
    """Get list of available symbols in database.

    Returns:
        List of symbol names
    """
    df = _query_df("SELECT DISTINCT symbol FROM dbbaroverview WHERE interval = 'd' ORDER BY symbol")
    return df["symbol"].to_list()


def get_symbol_data_range(symbol: str) -> dict[str, str | int] | None:
    """Get available date range for a symbol.

    Args:
        symbol: Trading symbol

    Returns:
        Dict with 'start' and 'end' dates, or None if not found
    """
    df = _query_df(
        """
            SELECT start, end, count FROM dbbaroverview
            WHERE symbol = ? AND interval = 'd'
        """,
        [symbol],
    )

    if df.is_empty():
        return None

    row = df.row(0, named=True)
    if row["start"] is None or row["end"] is None:
        return None

    return {
        "start": str(row["start"])[:10],
        "end": str(row["end"])[:10],
        "count": int(row["count"]),
    }


def load_bars_batch(
    symbols: list[str],
    start: datetime,
    end: datetime,
    exchange: Exchange = Exchange.LOCAL,
    interval: Interval = Interval.DAILY,
    lookback_days: int = 0,
) -> dict[str, list[BarData]]:
    """Load OHLCV bar data from database for multiple symbols.

    Args:
        symbols: List of trading symbols
        start: Start datetime
        end: End datetime
        exchange: Exchange (default: LOCAL)
        interval: Bar interval (default: DAILY)
        lookback_days: Extra days before start to load for volume lookback (default 0)

    Returns:
        Dictionary of symbol -> list of BarData objects
    """
    if not symbols:
        return {}

    effective_start = start
    if lookback_days > 0:
        from datetime import timedelta

        effective_start = start - timedelta(days=lookback_days)

    result: dict[str, list[BarData]] = {s: [] for s in symbols}
    batch_size = 500
    start_str = effective_start.strftime("%Y-%m-%d %H:%M:%S")
    end_str = end.strftime("%Y-%m-%d %H:%M:%S")

    for i in range(0, len(symbols), batch_size):
        batch = symbols[i : i + batch_size]
        placeholders = ",".join(["?"] * len(batch))
        df = _query_df(
            f"""
                SELECT symbol, exchange, interval, datetime,
                       open_price, high_price, low_price, close_price, volume
                FROM dbbardata
                WHERE symbol IN ({placeholders}) AND interval = 'd'
                  AND datetime >= ? AND datetime <= ?
                ORDER BY symbol, datetime
            """,
            [*batch, start_str, end_str],
        )

        for row in df.iter_rows(named=True):
            bar = BarData(
                symbol=str(row["symbol"]),
                exchange=Exchange(str(row["exchange"])),
                interval=Interval(str(row["interval"])),
                datetime=_parse_datetime(row["datetime"]),
                open_price=float(row["open_price"]),
                high_price=float(row["high_price"]),
                low_price=float(row["low_price"]),
                close_price=float(row["close_price"]),
                volume=float(row["volume"]),
            )
            if bar.symbol in result:
                result[bar.symbol].append(bar)

    total_bars = sum(len(bars) for bars in result.values())
    logger.info(f"Loaded {total_bars} bars for {len(symbols)} symbols")
    return result


def _parse_datetime(value: str | datetime) -> datetime:
    if isinstance(value, datetime):
        return value
    return datetime.strptime(str(value), "%Y-%m-%d %H:%M:%S")
