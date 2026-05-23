"""Unit tests for ASX announcement Pydantic models."""

import pytest
from pydantic import ValidationError

from app.analysis.models import Announcement, AnnouncementQuery, AnnouncementResult


class TestAnnouncement:
    """Announcement model validation."""

    def test_valid_announcement(self) -> None:
        ann = Announcement(
            ticker="BHP",
            date="2024-06-15",
            time="15:45",
            headline="Quarterly Report",
        )
        assert ann.ticker == "BHP"
        assert ann.price_sensitive is False
        assert ann.pages == 1
        assert ann.announcement_id == ""
        assert ann.pdf_url == ""

    def test_full_announcement(self) -> None:
        ann = Announcement(
            ticker="CBA",
            date="2024-01-30",
            time="09:30",
            headline="Appendix 4D - Half Year",
            price_sensitive=True,
            pages=12,
            announcement_id="abc123",
            pdf_url="https://www.asx.com.au/example.pdf",
        )
        assert ann.price_sensitive is True
        assert ann.pages == 12

    def test_requires_ticker(self) -> None:
        with pytest.raises(ValidationError):
            Announcement(
                date="2024-06-15",
                time="15:45",
                headline="Test",
            )

    def test_requires_date(self) -> None:
        with pytest.raises(ValidationError):
            Announcement(
                ticker="BHP",
                time="15:45",
                headline="Test",
            )

    def test_requires_headline(self) -> None:
        with pytest.raises(ValidationError):
            Announcement(
                ticker="BHP",
                date="2024-06-15",
                time="15:45",
            )

    def test_serialisation(self) -> None:
        ann = Announcement(
            ticker="BHP",
            date="2024-06-15",
            time="15:45",
            headline="Test",
        )
        data = ann.model_dump()
        assert data["ticker"] == "BHP"
        assert data["price_sensitive"] is False

    def test_json_serialisation(self) -> None:
        ann = Announcement(
            ticker="BHP",
            date="2024-06-15",
            time="15:45",
            headline="Test",
        )
        json_str = ann.model_dump_json()
        assert '"ticker":"BHP"' in json_str


class TestAnnouncementQuery:
    """AnnouncementQuery validation."""

    def test_defaults(self) -> None:
        query = AnnouncementQuery(ticker="BHP")
        assert query.period == "1M"
        assert query.price_sensitive_only is False

    def test_custom_period(self) -> None:
        query = AnnouncementQuery(ticker="BHP", period="3M")
        assert query.period == "3M"

    def test_price_sensitive_filter(self) -> None:
        query = AnnouncementQuery(ticker="BHP", price_sensitive_only=True)
        assert query.price_sensitive_only is True

    def test_requires_ticker(self) -> None:
        with pytest.raises(ValidationError):
            AnnouncementQuery()


class TestAnnouncementResult:
    """AnnouncementResult carries success/error end-to-end."""

    def test_success_result(self) -> None:
        result = AnnouncementResult(
            ticker="BHP",
            period_start="2024-01-01",
            period_end="2024-06-30",
            count=2,
            announcements=[
                Announcement(ticker="BHP", date="2024-03-15", time="09:30", headline="Q1 Report"),
                Announcement(
                    ticker="BHP",
                    date="2024-06-15",
                    time="15:45",
                    headline="Q2 Report",
                    price_sensitive=True,
                ),
            ],
        )
        assert result.success is True
        assert result.error is None
        assert result.count == 2

    def test_failure_result(self) -> None:
        result = AnnouncementResult(
            ticker="BHP",
            period_start="2024-01-01",
            period_end="2024-06-30",
            count=0,
            success=False,
            error="HTTP 503: ASX unavailable",
            announcements=[],
        )
        assert result.success is False
        assert result.error == "HTTP 503: ASX unavailable"
        assert result.count == 0

    def test_zero_matches_is_success(self) -> None:
        """Zero matches on a quiet day is still success=True."""
        result = AnnouncementResult(
            ticker="XYZ",
            period_start="2024-01-01",
            period_end="2024-01-31",
            count=0,
            announcements=[],
        )
        assert result.success is True
        assert result.error is None

    def test_count_matches_announcements_length(self) -> None:
        announcements = [
            Announcement(ticker="BHP", date="2024-03-15", time="09:30", headline="Q1"),
        ]
        result = AnnouncementResult(
            ticker="BHP",
            period_start="2024-01-01",
            period_end="2024-06-30",
            count=1,
            announcements=announcements,
        )
        assert result.count == len(result.announcements)
