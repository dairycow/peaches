"""Data loading utilities for analysis."""

import sqlite3
from pathlib import Path

from app.config import config


def _query(query: str, params: list[str] | None = None) -> list[tuple]:
    db_path = str(Path(config.database.path))
    conn = sqlite3.connect(db_path)
    cur = conn.execute(query, params or [])
    rows = cur.fetchall()
    conn.close()
    return rows


def list_available_symbols() -> list[str]:
    """Get list of available symbols in database.

    Returns:
        List of symbol names
    """
    rows = _query("SELECT DISTINCT symbol FROM dbbaroverview WHERE interval = 'd' ORDER BY symbol")
    return [row[0] for row in rows]


def get_symbol_data_range(symbol: str) -> dict[str, str | int] | None:
    """Get available date range for a symbol.

    Args:
        symbol: Trading symbol

    Returns:
        Dict with 'start' and 'end' dates, or None if not found
    """
    rows = _query(
        """
            SELECT start, end, count FROM dbbaroverview
            WHERE symbol = ? AND interval = 'd'
        """,
        [symbol],
    )

    if not rows:
        return None

    start, end, count = rows[0]
    if start is None or end is None:
        return None

    return {
        "start": str(start)[:10],
        "end": str(end)[:10],
        "count": int(count),
    }
