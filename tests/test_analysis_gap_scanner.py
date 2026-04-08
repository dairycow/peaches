"""Tests for GapScanner."""

from datetime import date, datetime
from typing import cast
from unittest.mock import MagicMock

import pytest
from vnpy.trader.object import BarData

from app.analysis.scanners.gap_scanner import GapScanner
from app.analysis.stock_data import StockData


def _make_bar(
    symbol: str = "TEST",
    dt: datetime | None = None,
    open_price: float = 10.0,
    high: float = 11.0,
    low: float = 9.0,
    close: float = 10.5,
    volume: int = 100000,
) -> BarData:
    bar = MagicMock(spec=BarData)
    bar.symbol = symbol
    bar.datetime = dt or datetime(2024, 1, 1)
    bar.open_price = open_price
    bar.high_price = high
    bar.low_price = low
    bar.close_price = close
    bar.volume = volume
    return cast(BarData, bar)


def _make_bars(
    symbol: str = "TEST",
    closes: list[float] | None = None,
    opens: list[float] | None = None,
    volumes: list[int] | None = None,
    start_date: date = date(2024, 1, 1),
) -> list[BarData]:
    n = len(closes) if closes else 0
    if opens is None:
        opens = closes or []
    if closes is None:
        closes = opens
    if volumes is None:
        volumes = [100000] * n

    bars = []
    for i in range(n):
        dt = datetime.combine(
            date(start_date.year, start_date.month, start_date.day + i),
            datetime.min.time(),
        )
        bars.append(
            _make_bar(
                symbol=symbol,
                dt=dt,
                open_price=opens[i],
                high=max(opens[i], closes[i]) + 0.5,
                low=min(opens[i], closes[i]) - 0.5,
                close=closes[i],
                volume=volumes[i],
            )
        )
    return bars


def test_creation():
    scanner = GapScanner({})
    assert scanner.stocks == {}


def test_gap_up_detection():
    closes = [10.0, 10.0, 10.0, 10.0, 10.0]
    opens = [10.0, 10.0, 12.0, 10.0, 10.0]
    bars = _make_bars(closes=closes, opens=opens, start_date=date(2024, 1, 1))
    stock = StockData("TEST", bars)
    scanner = GapScanner({"TEST": stock})

    gaps = scanner.find_gaps(
        start_date=datetime(2024, 1, 1),
        end_date=datetime(2024, 1, 31),
        gap_threshold=5.0,
        volume_multiplier=0,
        min_volume=0,
        direction="up",
    )

    assert len(gaps) == 1
    assert gaps[0]["direction"] == "up"
    assert gaps[0]["gap_percent"] == pytest.approx(20.0)


def test_gap_down_detection():
    closes = [10.0, 10.0, 10.0, 10.0, 10.0]
    opens = [10.0, 10.0, 8.0, 10.0, 10.0]
    bars = _make_bars(closes=closes, opens=opens, start_date=date(2024, 1, 1))
    stock = StockData("TEST", bars)
    scanner = GapScanner({"TEST": stock})

    gaps = scanner.find_gaps(
        start_date=datetime(2024, 1, 1),
        end_date=datetime(2024, 1, 31),
        gap_threshold=5.0,
        volume_multiplier=0,
        min_volume=0,
        direction="down",
    )

    assert len(gaps) == 1
    assert gaps[0]["direction"] == "down"
    assert gaps[0]["gap_percent"] == pytest.approx(-20.0)


def test_both_directions_sorted_by_absolute():
    closes = [10.0, 10.0, 10.0, 10.0, 10.0, 10.0, 10.0]
    opens = [10.0, 11.0, 12.0, 10.0, 8.5, 10.0, 10.0]
    bars = _make_bars(closes=closes, opens=opens, start_date=date(2024, 1, 1))
    stock = StockData("TEST", bars)
    scanner = GapScanner({"TEST": stock})

    gaps = scanner.find_gaps(
        start_date=datetime(2024, 1, 1),
        end_date=datetime(2024, 1, 31),
        gap_threshold=5.0,
        volume_multiplier=0,
        min_volume=0,
        direction="both",
        sort_absolute=True,
    )

    assert len(gaps) == 3
    assert abs(gaps[0]["gap_percent"]) >= abs(gaps[1]["gap_percent"])
    assert abs(gaps[1]["gap_percent"]) >= abs(gaps[2]["gap_percent"])


def test_volume_filter_bypass():
    closes = [10.0, 10.0, 10.0]
    opens = [10.0, 12.0, 10.0]
    volumes = [100, 100, 100]
    bars = _make_bars(closes=closes, opens=opens, volumes=volumes, start_date=date(2024, 1, 1))
    stock = StockData("TEST", bars)
    scanner = GapScanner({"TEST": stock})

    gaps = scanner.find_gaps(
        start_date=datetime(2024, 1, 1),
        end_date=datetime(2024, 1, 31),
        gap_threshold=5.0,
        volume_multiplier=0,
        min_volume=0,
        direction="up",
    )

    assert len(gaps) == 1


def test_empty_data():
    stock = StockData("TEST", [])
    scanner = GapScanner({"TEST": stock})

    gaps = scanner.find_gaps(
        start_date=datetime(2024, 1, 1),
        end_date=datetime(2024, 1, 31),
        gap_threshold=5.0,
        direction="both",
    )

    assert gaps == []


def test_single_bar():
    bars = _make_bars(closes=[10.0], opens=[10.0], start_date=date(2024, 1, 1))
    stock = StockData("TEST", bars)
    scanner = GapScanner({"TEST": stock})

    gaps = scanner.find_gaps(
        start_date=datetime(2024, 1, 1),
        end_date=datetime(2024, 1, 31),
        gap_threshold=5.0,
        direction="both",
    )

    assert gaps == []


def test_below_threshold_excluded():
    closes = [10.0, 10.0]
    opens = [10.0, 10.3]
    bars = _make_bars(closes=closes, opens=opens, start_date=date(2024, 1, 1))
    stock = StockData("TEST", bars)
    scanner = GapScanner({"TEST": stock})

    gaps = scanner.find_gaps(
        start_date=datetime(2024, 1, 1),
        end_date=datetime(2024, 1, 31),
        gap_threshold=5.0,
        volume_multiplier=0,
        min_volume=0,
        direction="both",
    )

    assert len(gaps) == 0


def test_min_price_filter():
    closes = [10.0, 0.05, 0.05]
    opens = [10.0, 10.0, 0.06]
    bars = _make_bars(closes=closes, opens=opens, start_date=date(2024, 1, 1))
    stock = StockData("TEST", bars)
    scanner = GapScanner({"TEST": stock})

    gaps = scanner.find_gaps(
        start_date=datetime(2024, 1, 1),
        end_date=datetime(2024, 1, 31),
        gap_threshold=5.0,
        volume_multiplier=0,
        min_volume=0,
        direction="both",
        min_price=0.20,
    )

    assert len(gaps) == 0

    gaps_no_filter = scanner.find_gaps(
        start_date=datetime(2024, 1, 1),
        end_date=datetime(2024, 1, 31),
        gap_threshold=5.0,
        volume_multiplier=0,
        min_volume=0,
        direction="both",
        min_price=0.0,
    )

    assert len(gaps_no_filter) == 1


def test_exclude_options():
    from app.analysis.scanners.gap_scanner import is_option_code

    assert not is_option_code("BHP")
    assert not is_option_code("RIO")
    assert not is_option_code("CBA")
    assert not is_option_code("COL")
    assert not is_option_code("COS")
    assert not is_option_code("BOQ")
    assert not is_option_code("ECL")
    assert not is_option_code("IO")
    assert not is_option_code("IOD")

    assert is_option_code("BHPKOA")
    assert is_option_code("ANZKOB")
    assert is_option_code("CBAJOA")
    assert is_option_code("TLSWOB")
    assert is_option_code("BHPKOL")
    assert is_option_code("3DAO")
    assert is_option_code("CC5OA")
    assert is_option_code("ECLIOA")
    assert is_option_code("STOKOR")
    assert is_option_code("ANZSO1")
    assert is_option_code("1ADO")
