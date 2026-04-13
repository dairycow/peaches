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
class AnnouncementGapScanStartedEvent(AppEvent):
    """Announcement gap scan started."""

    pass


@dataclass
class AnnouncementGapScanCompletedEvent(AppEvent):
    """Announcement gap scan finished."""

    count: int
    success: bool
    error: str | None
