"""CSV importer for ASX historical data."""

from datetime import datetime
from pathlib import Path
from typing import TypedDict

import polars as pl
from loguru import logger
from vnpy.trader.constant import Exchange, Interval
from vnpy.trader.object import BarData

from app.database import DatabaseManager, get_database_manager


class ImportResult(TypedDict):
    file: str
    status: str
    total_bars: int | None
    reason: str | None


class ImportSummary(TypedDict):
    total_files: int
    success: int
    skipped: int
    errors: int
    total_bars_imported: int
    results: list[ImportResult]


class CSVImporter:
    """CSV importer for ASX historical data."""

    def __init__(self, csv_dir: str | Path, db_manager: "DatabaseManager") -> None:
        """Initialize CSV importer.

        Args:
            csv_dir: Directory containing CSV files
            db_manager: Database manager instance
        """
        self.csv_dir = Path(csv_dir)
        self.db_manager = db_manager

    def _parse_csv(self, filepath: Path) -> pl.DataFrame:
        """Parse CSV file using polars.

        Args:
            filepath: Path to CSV file

        Returns:
            Polars DataFrame with OHLCV data
        """
        df = pl.read_csv(
            filepath,
            has_header=False,
            new_columns=["symbol", "date", "open", "high", "low", "close", "volume"],
            schema_overrides={
                "symbol": pl.Utf8,
                "date": pl.Utf8,
                "open": pl.Float64,
                "high": pl.Float64,
                "low": pl.Float64,
                "close": pl.Float64,
                "volume": pl.Int64,
            },
        )

        df = df.with_columns(pl.col("date").str.strptime(pl.Date, "%d/%m/%Y"))

        return df.sort("date")

    def _convert_to_bars(self, df: pl.DataFrame) -> list[BarData]:
        """Convert DataFrame to vn.py BarData objects.

        Args:
            df: Input DataFrame with symbol column

        Returns:
            List of BarData objects
        """
        bars: list[BarData] = []

        for row in df.iter_rows(named=True):
            try:
                symbol = str(row["symbol"]).upper()
                bar = BarData(
                    symbol=symbol,
                    exchange=Exchange.LOCAL,
                    interval=Interval.DAILY,
                    datetime=datetime.combine(row["date"], datetime.min.time()),
                    open_price=float(row["open"]),
                    high_price=float(row["high"]),
                    low_price=float(row["low"]),
                    close_price=float(row["close"]),
                    volume=int(row["volume"]),
                    gateway_name="",
                )

                bars.append(bar)

            except Exception as e:
                logger.warning(f"Failed to convert row to bar: {e}")
                continue

        logger.info(f"Converted {len(bars)} valid bars")
        return bars

    def import_file(self, filepath: Path) -> ImportResult:
        """Import a single CSV file.

        Args:
            filepath: Path to CSV file

        Returns:
            Import result dictionary
        """
        try:
            logger.info(f"Importing {filepath.name}")

            df = self._parse_csv(filepath)

            if len(df) == 0:
                return ImportResult(
                    file=filepath.name, status="skipped", total_bars=None, reason="no data"
                )

            bars = self._convert_to_bars(df)
            total_bars = len(bars)

            if self.db_manager.save_bars(bars, stream=True):
                logger.info(f"Imported {total_bars} bars from {filepath.name}")
                return ImportResult(
                    file=filepath.name,
                    status="success",
                    total_bars=total_bars,
                    reason=None,
                )
            else:
                return ImportResult(
                    file=filepath.name,
                    status="error",
                    total_bars=None,
                    reason="database save failed",
                )

        except Exception as e:
            logger.error(f"Failed to import {filepath.name}: {e}")
            return ImportResult(
                file=filepath.name,
                status="error",
                total_bars=None,
                reason=str(e),
            )

    def import_all(self) -> ImportSummary:
        """Import all CSV files from directory.

        Returns:
            Import summary dictionary
        """
        csv_files = sorted(self.csv_dir.glob("**/*.csv"))

        if not csv_files:
            logger.warning(f"No CSV files found in {self.csv_dir}")
            return ImportSummary(
                total_files=0,
                success=0,
                skipped=0,
                errors=0,
                total_bars_imported=0,
                results=[],
            )

        logger.info(f"Starting import of {len(csv_files)} files")

        processed_files_path = self.csv_dir / ".processed_files.txt"
        processed_files = self._load_processed_files(processed_files_path)

        results = []
        success = 0
        skipped = 0
        errors = 0
        total_bars_imported = 0
        newly_processed_files = []

        for filepath in csv_files:
            if str(filepath) in processed_files:
                logger.info(f"Skipping already processed file: {filepath.name}")
                skipped += 1
                continue

            result = self.import_file(filepath)
            results.append(result)

            if result["status"] == "success":
                success += 1
                if result["total_bars"] is not None:
                    total_bars_imported += result["total_bars"]
                newly_processed_files.append(str(filepath))
            elif result["status"] == "skipped":
                skipped += 1
            else:
                errors += 1

        self._save_processed_files(processed_files_path, processed_files, newly_processed_files)

        summary = ImportSummary(
            total_files=len(csv_files),
            success=success,
            skipped=skipped,
            errors=errors,
            total_bars_imported=total_bars_imported,
            results=results,
        )

        logger.info(
            f"Import complete: {success} succeeded, {skipped} skipped, {errors} errors, {total_bars_imported} total bars"
        )

        return summary

    def _load_processed_files(self, filepath: Path) -> set[str]:
        """Load list of processed files.

        Args:
            filepath: Path to processed files tracking file

        Returns:
            Set of processed file paths
        """
        processed_files: set[str] = set()
        if filepath.exists():
            try:
                with open(filepath) as f:
                    processed_files = {line.strip() for line in f if line.strip()}
                logger.info(f"Loaded {len(processed_files)} processed files from tracking")
            except Exception as e:
                logger.warning(f"Failed to load processed files tracking: {e}")
        return processed_files

    def _save_processed_files(self, filepath: Path, existing: set[str], new: list[str]) -> None:
        """Save list of processed files.

        Args:
            filepath: Path to processed files tracking file
            existing: Set of existing processed files
            new: List of newly processed files
        """
        all_processed = existing | set(new)
        try:
            with open(filepath, "w") as f:
                for processed_file in sorted(all_processed):
                    f.write(f"{processed_file}\n")
            logger.info(f"Saved {len(new)} newly processed files to tracking")
        except Exception as e:
            logger.warning(f"Failed to save processed files tracking: {e}")


def create_importer(csv_dir: str | Path) -> CSVImporter:
    """Create configured CSV importer.

    Args:
        csv_dir: Directory containing CSV files

    Returns:
        CSVImporter instance
    """
    db_manager = get_database_manager()
    return CSVImporter(csv_dir=csv_dir, db_manager=db_manager)
