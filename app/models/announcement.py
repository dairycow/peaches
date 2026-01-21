"""Announcement domain models."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Announcement:
    """Domain model for company announcements."""

    ticker: str
    headline: str
    timestamp: str
    url: str | None = None

    def __str__(self) -> str:
        return f"{self.ticker}: {self.headline}"
