"""Application event definitions."""

from dataclasses import dataclass
from datetime import datetime

from app.events.bus import Event


@dataclass
class AppEvent(Event):
    """Base class for all application events."""

    source: str
    correlation_id: str


@dataclass
class ScanStartedEvent(AppEvent):
    """Scanner started running."""

    pass


@dataclass
class AnnouncementFoundEvent(AppEvent):
    """Price-sensitive announcement discovered."""

    ticker: str
    headline: str
    date: str
    time: str
    timestamp: datetime


@dataclass
class ScanCompletedEvent(AppEvent):
    """Scanner finished running."""

    total_announcements: int
    processed_count: int
    success: bool
    error: str | None


@dataclass
class DownloadStartedEvent(AppEvent):
    """Download started."""

    target_date: str | None


@dataclass
class DownloadCompletedEvent(AppEvent):
    """Download finished."""

    filepath: str | None
    status: str
    reason: str | None


@dataclass
class ImportStartedEvent(AppEvent):
    """CSV import started."""

    pass


@dataclass
class ImportCompletedEvent(AppEvent):
    """CSV import finished."""

    total_bars: int | None
    success: int | None
    errors: int | None
    skipped: int | None
    total_files: int | None
    status: str


@dataclass
class AnnouncementGapScanStartedEvent(AppEvent):
    """Announcement gap scan started."""

    pass


@dataclass
class AnnouncementGapCandidateFoundEvent(AppEvent):
    """Single announcement gap candidate found."""

    symbol: str
    gap_pct: float
    six_month_high: float
    current_price: float
    announcement_headline: str
    announcement_time: datetime
    exchange: str = "ASX"


@dataclass
class AnnouncementGapScanCompletedEvent(AppEvent):
    """Announcement gap scan finished."""

    count: int
    success: bool
    error: str | None
