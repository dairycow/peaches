"""Database manager wrapper for vn.py."""

from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

import peewee
from loguru import logger
from vnpy.trader.constant import Exchange, Interval
from vnpy.trader.database import BarOverview, BaseDatabase, get_database
from vnpy.trader.object import BarData

from app.config import config

if TYPE_CHECKING:
    pass


class DbBarOverview(peewee.Model):
    """Peewee model for vn.py dbbaroverview table."""

    symbol = peewee.CharField()
    exchange = peewee.CharField()
    interval = peewee.CharField()
    start = peewee.DateField()
    end = peewee.DateField()
    count = peewee.IntegerField()

    class Meta:
        db_table = "dbbaroverview"


class DatabaseManager:
    """Database manager wrapper for vn.py."""

    def __init__(self) -> None:
        """Initialize database manager."""
        self._database: BaseDatabase | None = None

    @property
    def database(self) -> BaseDatabase:
        """Get database instance.

        Returns:
            BaseDatabase instance

        Raises:
            RuntimeError: If database is not initialized
        """
        if self._database is None:
            self._database = get_database()
        return self._database

    def save_bars(self, bars: list[BarData], stream: bool = False) -> bool:
        """Save bar data to database.

        Args:
            bars: List of BarData objects to save

        Returns:
            True if successful, False otherwise
        """
        try:
            result = self.database.save_bar_data(bars, stream=stream)
            if result:
                logger.info(f"Saved {len(bars)} bars to database")
            else:
                logger.warning(f"Failed to save {len(bars)} bars to database")
            return result
        except Exception as e:
            logger.error(f"Error saving bars to database: {e}")
            return False

    def load_bars(
        self,
        symbol: str,
        exchange: Exchange,
        interval: Interval,
        start: datetime | None = None,
        end: datetime | None = None,
    ) -> list[BarData]:
        """Load bar data from database.

        Args:
            symbol: Symbol name
            exchange: Exchange enum
            interval: Interval enum
            start: Start datetime (optional)
            end: End datetime (optional)

        Returns:
            List of BarData objects
        """
        try:
            start_dt = start if start else datetime(1900, 1, 1)
            end_dt = end if end else datetime.now()
            bars = self.database.load_bar_data(symbol, exchange, interval, start_dt, end_dt)
            logger.info(f"Loaded {len(bars)} bars for {symbol}.{exchange}-{interval}")
            return bars
        except Exception as e:
            logger.error(f"Error loading bars from database: {e}")
            return []

    def get_overview(self) -> list[BarOverview]:
        """Get database overview of available bar data.

        Returns:
            List of BarOverview objects
        """
        try:
            overview = self.database.get_bar_overview()
            logger.info(f"Database contains {len(overview)} symbols")
            return overview
        except Exception as e:
            logger.error(f"Error getting database overview: {e}")
            return []

    def get_stats(self) -> dict[str, int | dict[str, int]]:
        """Get database statistics.

        Returns:
            Dictionary with statistics
        """
        overview = self.get_overview()
        total_bars = sum(item.count for item in overview)
        unique_symbols = len({item.symbol for item in overview})

        interval_count: dict[str, int] = {}
        for item in overview:
            interval_str = str(item.interval)
            interval_count[interval_str] = interval_count.get(interval_str, 0) + 1

        stats: dict[str, int | dict[str, int]] = {
            "total_symbols": len(overview),
            "unique_symbols": unique_symbols,
            "total_bars": total_bars,
            "interval_breakdown": interval_count,
        }

        return stats

    def get_database_stats(self) -> dict[str, str | int | float]:
        """Get database statistics for API.

        Returns:
            Dictionary with database stats including size
        """
        db_path = Path(config.historical_data.db_path)
        db_size = db_path.stat().st_size if db_path.exists() else 0

        overview = self.get_overview()
        total_bars = sum(item.count for item in overview)

        return {
            "db_path": str(db_path),
            "db_size_bytes": db_size,
            "db_size_mb": round(db_size / (1024 * 1024), 2),
            "total_symbols": len(overview),
            "total_bars": total_bars,
        }

    def get_database_overview(self) -> dict[str, int | list[dict[str, str | int | None]]]:
        """Get database overview for API.

        Returns:
            Dictionary with symbol details
        """
        overview = self.get_overview()

        return {
            "total_symbols": len(overview),
            "symbols": [
                {
                    "symbol": o.symbol,
                    "exchange": str(o.exchange),
                    "interval": str(o.interval),
                    "count": o.count,
                    "start": o.start.isoformat() if o.start else None,
                    "end": o.end.isoformat() if o.end else None,
                }
                for o in overview
            ],
        }

    def rebuild_overview(self) -> bool:
        """Rebuild bar overview table from actual bar data.

        Returns:
            True if successful, False otherwise
        """
        try:
            logger.info("Rebuilding bar overview table")

            DbBarOverview.bind(self.database.db)  # type: ignore[attr-defined]
            DbBarOverview.delete().execute()

            logger.info("Deleted existing bar overview records")

            self.database.init_bar_overview()  # type: ignore[attr-defined]

            logger.info("Successfully rebuilt bar overview table")
            return True
        except Exception as e:
            logger.error(f"Error rebuilding bar overview: {e}")
            return False


_database_manager: DatabaseManager | None = None


def get_database_manager() -> DatabaseManager:
    """Get singleton database manager instance.

    Returns:
        DatabaseManager singleton instance
    """
    global _database_manager
    if _database_manager is None:
        _database_manager = DatabaseManager()
    return _database_manager
