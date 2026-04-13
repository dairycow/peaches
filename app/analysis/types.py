"""Local type definitions for analysis module."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum


class Interval(StrEnum):
    DAILY = "d"
    MINUTE = "1m"
    HOUR = "1h"


class Exchange(StrEnum):
    LOCAL = "LOCAL"


@dataclass
class BarData:
    symbol: str
    exchange: Exchange = Exchange.LOCAL
    interval: Interval = Interval.DAILY
    datetime: datetime = datetime(2000, 1, 1)
    open_price: float = 0.0
    high_price: float = 0.0
    low_price: float = 0.0
    close_price: float = 0.0
    volume: float = 0.0
