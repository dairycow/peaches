"""Database manager for bar data read access using peewee and SQLite."""

from datetime import datetime
from pathlib import Path
from typing import Any

import peewee
from loguru import logger

from app.analysis.types import BarData, Exchange, Interval
from app.config import config

database_proxy = peewee.DatabaseProxy()


class DbBarData(peewee.Model):
    """Peewee model for dbbardata table."""

    symbol = peewee.CharField()
    exchange = peewee.CharField()
    datetime = peewee.DateTimeField()
    interval = peewee.CharField()
    volume = peewee.FloatField(default=0.0)
    turnover = peewee.FloatField(default=0.0)
    open_interest = peewee.FloatField(default=0.0)
    open_price = peewee.FloatField()
    high_price = peewee.FloatField()
    low_price = peewee.FloatField()
    close_price = peewee.FloatField()

    class Meta:
        database = database_proxy
        table_name = "dbbardata"
        indexes = ((("symbol", "exchange", "interval", "datetime"), True),)


class DbBarOverview(peewee.Model):
    """Peewee model for dbbaroverview table."""

    symbol = peewee.CharField()
    exchange = peewee.CharField()
    interval = peewee.CharField()
    count = peewee.IntegerField()
    start = peewee.DateTimeField()
    end = peewee.DateTimeField()

    class Meta:
        database = database_proxy
        table_name = "dbbaroverview"
        indexes = ((("symbol", "exchange", "interval"), True),)


def initialise_database() -> str:
    """Connect to the SQLite database (read-only consumer).

    Returns:
        Database file path
    """
    db_path = str(Path(config.database.path))

    db = peewee.SqliteDatabase(
        db_path,
        pragmas={
            "journal_mode": "wal",
            "cache_size": -1024 * 64,
            "foreign_keys": 1,
        },
    )
    database_proxy.initialize(db)

    db.connect(reuse_if_open=True)

    return db_path


class DatabaseManager:
    """Database manager for bar data read access."""

    def __init__(self) -> None:
        """Initialize database manager."""
        self._db: peewee.SqliteDatabase | None = None

    @property
    def db(self) -> peewee.SqliteDatabase:
        """Get database instance.

        Returns:
            SqliteDatabase instance

        Raises:
            RuntimeError: If database is not initialized
        """
        if self._db is None:
            self._db = database_proxy.obj
            if self._db is None:
                raise RuntimeError("Database not initialised. Call initialise_database() first.")
        return self._db

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
            query = DbBarData.select().where(
                DbBarData.symbol == symbol,
                DbBarData.exchange == str(exchange),
                DbBarData.interval == str(interval),
            )

            if start:
                query = query.where(DbBarData.datetime >= start)
            if end:
                query = query.where(DbBarData.datetime <= end)

            query = query.order_by(DbBarData.datetime)

            bars = []
            for row in query:
                bars.append(
                    BarData(
                        symbol=row.symbol,
                        exchange=Exchange(row.exchange),
                        interval=Interval(row.interval),
                        datetime=row.datetime,
                        open_price=row.open_price,
                        high_price=row.high_price,
                        low_price=row.low_price,
                        close_price=row.close_price,
                        volume=row.volume,
                    )
                )

            logger.info(f"Loaded {len(bars)} bars for {symbol}.{exchange}-{interval}")
            return bars
        except Exception as e:
            logger.error(f"Error loading bars from database: {e}")
            return []

    def get_overview(self) -> list[Any]:
        """Get database overview of available bar data.

        Returns:
            List of DbBarOverview objects
        """
        try:
            overview = list(DbBarOverview.select())
            logger.info(f"Database contains {len(overview)} symbols")
            return overview
        except Exception as e:
            logger.error(f"Error getting database overview: {e}")
            return []

    def get_database_stats(self) -> dict[str, str | int | float]:
        """Get database statistics for API.

        Returns:
            Dictionary with database stats including size
        """
        db_path = Path(config.database.path)
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
