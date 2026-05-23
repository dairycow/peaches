"""Pydantic models for ASX announcements."""

from pydantic import BaseModel, Field


class Announcement(BaseModel):
    """A single ASX company announcement."""

    ticker: str = Field(..., description="ASX ticker symbol")
    date: str = Field(..., description="Announcement date (YYYY-MM-DD)")
    time: str = Field(..., description="Announcement time (HH:MM 24hr)")
    headline: str = Field(..., description="Announcement headline")
    price_sensitive: bool = Field(default=False, description="Whether price-sensitive")
    pages: int = Field(default=1, description="Number of pages in PDF")
    announcement_id: str = Field(default="", description="ASX announcement ID")
    pdf_url: str = Field(default="", description="URL to announcement PDF")


class AnnouncementQuery(BaseModel):
    """Parameters for an announcement query."""

    ticker: str = Field(..., description="ASX ticker symbol")
    period: str = Field(default="1M", description="Period shorthand or date range")
    price_sensitive_only: bool = Field(default=False, description="Filter to price-sensitive only")


class AnnouncementResult(BaseModel):
    """Result of an announcement query.

    Carries success/error for end-to-end propagation.
    Consumers MUST check success before trusting count=0 as 'quiet day'.
    """

    ticker: str
    period_start: str
    period_end: str
    count: int
    success: bool = Field(default=True, description="False if scrape failed")
    error: str | None = Field(default=None, description="Error message if success=False")
    announcements: list[Announcement]
