from datetime import date, datetime
from pathlib import Path

import polars as pl


def test_parse_csv_line():
    """Test parsing a single CSV line."""
    line = "BHP,14/01/2026,30.7,30.96,30.3,30.3,613098"
    parts = line.split(",")

    assert parts[0] == "BHP"
    assert parts[1] == "14/01/2026"
    assert float(parts[2]) == 30.7
    assert float(parts[3]) == 30.96
    assert int(parts[6]) == 613098


def test_parse_csv_file(tmp_path: Path):
    """Test parsing a full CSV file with polars."""
    csv_file = tmp_path / "test.csv"
    csv_file.write_text(
        """BHP,14/01/2026,30.7,30.96,30.3,30.3,613098
CBA,14/01/2026,110.5,111.2,110.1,110.8,2450123
"""
    )

    df = pl.read_csv(
        csv_file,
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

    assert len(df) == 2
    assert df.row(0, named=True)["symbol"] == "BHP"
    assert df.row(1, named=True)["symbol"] == "CBA"
    assert df.row(0, named=True)["date"] == date(2026, 1, 14)


def test_csv_date_parsing():
    """Test DD/MM/YYYY date format parsing."""
    from datetime import date

    df = pl.DataFrame(
        {"date": ["14/01/2026", "15/01/2026"]},
        schema={"date": pl.Utf8},
    )

    df = df.with_columns(pl.col("date").str.strptime(pl.Date, "%d/%m/%Y"))

    assert df.row(0, named=True)["date"] == date(2026, 1, 14)
    assert df.row(1, named=True)["date"] == date(2026, 1, 15)


def test_bardata_creation():
    """Test BarData object creation."""
    from vnpy.trader.constant import Exchange, Interval
    from vnpy.trader.object import BarData

    bar = BarData(
        symbol="BHP",
        exchange=Exchange.LOCAL,
        interval=Interval.DAILY,
        datetime=datetime.combine(date(2026, 1, 14), datetime.min.time()),
        open_price=30.7,
        high_price=30.96,
        low_price=30.3,
        close_price=30.3,
        volume=613098,
        gateway_name="",
    )

    assert bar.symbol == "BHP"
    assert bar.exchange == Exchange.LOCAL
    assert bar.interval == Interval.DAILY
    assert bar.open_price == 30.7
    assert bar.volume == 613098
