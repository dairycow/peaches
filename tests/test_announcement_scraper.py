"""Unit tests for the historical ASX announcement scraper.

Tests use mocked HTTP responses to avoid hitting ASX in unit tests.
Covers: valid scrape, HTTP failure, malformed rows, date filtering, period parsing.
"""

from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

import httpx
import pytest

from app.analysis.announcement_scraper import (
    AnnouncementScraper,
    filter_announcements_by_date_range,
)
from app.analysis.models import Announcement, AnnouncementResult


VALID_HTML = """
<div id="content">
  <div>
    <announcement_data>
      <table>
        <tr><th>Date</th><th>Sensitivity</th><th>Headline</th></tr>
        <tr>
          <td>
            <span>Icon</span>
            15/06/2024
            3:45 pm
          </td>
          <td><img class="pricesens" src="/icon.png" /></td>
          <td>
            <a href="/asx/pdf/test.pdf">PDF</a>
            Quarterly Activities Report
            <span class="page">5 page(s)</span>
          </td>
        </tr>
        <tr>
          <td>
            <span>Icon</span>
            01/03/2024
            9:30 am
          </td>
          <td></td>
          <td>
            <a href="/asx/pdf/test2.pdf">PDF</a>
            Director's Interest Notice
            <span class="page">2 page(s)</span>
          </td>
        </tr>
      </table>
    </announcement_data>
  </div>
</div>
"""

MALFORMED_ROW_HTML = """
<div id="content">
  <div>
    <announcement_data>
      <table>
        <tr><th>Date</th><th>Sensitivity</th><th>Headline</th></tr>
        <tr>
          <td>
            <span>Icon</span>
            15/06/2024
            3:45 pm
          </td>
          <td><img class="pricesens" src="/icon.png" /></td>
          <td>
            <a href="/asx/pdf/good.pdf">PDF</a>
            Good Announcement
            <span class="page">3 page(s)</span>
          </td>
        </tr>
        <tr>
          <td>Bad row with no links</td>
          <td></td>
          <td>No anchor here</td>
        </tr>
        <tr>
          <td>
            <span>Icon</span>
            not/a/date
            3:45 pm
          </td>
          <td></td>
          <td>
            <a href="/asx/pdf/bad-date.pdf">PDF</a>
            Bad Date Announcement
            <span class="page">1 page(s)</span>
          </td>
        </tr>
      </table>
    </announcement_data>
  </div>
</div>
"""

EMPTY_TABLE_HTML = """
<div id="content">
  <div>
    <announcement_data>
      <table>
        <tr><th>Date</th><th>Sensitivity</th><th>Headline</th></tr>
      </table>
    </announcement_data>
  </div>
</div>
"""

NO_TABLE_HTML = """
<div id="content">
  <div>No announcements found</div>
</div>
"""


def _mock_response(text: str, status_code: int = 200) -> httpx.Response:
    return httpx.Response(status_code=status_code, text=text, request=httpx.Request("GET", "https://example.com"))


class TestScrapeAnnouncementsForYear:
    """Tests for scrape_announcements_for_year with mocked HTTP."""

    @patch("app.analysis.announcement_scraper.httpx.get")
    def test_valid_scrape(self, mock_get: MagicMock) -> None:
        from app.analysis.announcement_scraper import scrape_announcements_for_year

        mock_get.return_value = _mock_response(VALID_HTML)

        results = scrape_announcements_for_year("BHP", 2024)

        assert len(results) == 2
        assert all(isinstance(a, Announcement) for a in results)

        first = results[0]
        assert first.ticker == "BHP"
        assert first.date == "2024-06-15"
        assert first.time == "15:45"
        assert first.headline == "Quarterly Activities Report"
        assert first.price_sensitive is True
        assert first.pages == 5
        assert first.announcement_id == ""
        assert first.pdf_url == ""

    @patch("app.analysis.announcement_scraper.httpx.get")
    def test_malformed_rows_skipped(self, mock_get: MagicMock) -> None:
        from app.analysis.announcement_scraper import scrape_announcements_for_year

        mock_get.return_value = _mock_response(MALFORMED_ROW_HTML)

        results = scrape_announcements_for_year("BHP", 2024)

        assert len(results) == 1
        assert results[0].headline == "Good Announcement"
        assert results[0].date == "2024-06-15"

    @patch("app.analysis.announcement_scraper.httpx.get")
    def test_empty_table(self, mock_get: MagicMock) -> None:
        from app.analysis.announcement_scraper import scrape_announcements_for_year

        mock_get.return_value = _mock_response(EMPTY_TABLE_HTML)

        results = scrape_announcements_for_year("BHP", 2024)

        assert results == []

    @patch("app.analysis.announcement_scraper.httpx.get")
    def test_no_table(self, mock_get: MagicMock) -> None:
        from app.analysis.announcement_scraper import scrape_announcements_for_year

        mock_get.return_value = _mock_response(NO_TABLE_HTML)

        results = scrape_announcements_for_year("BHP", 2024)

        assert results == []

    @patch("app.analysis.announcement_scraper.httpx.get")
    def test_http_error_propagates(self, mock_get: MagicMock) -> None:
        from app.analysis.announcement_scraper import scrape_announcements_for_year

        mock_get.return_value = _mock_response("", status_code=500)
        mock_get.return_value.raise_for_status = lambda: (_ for _ in ()).throw(
            httpx.HTTPStatusError("500", request=httpx.Request("GET", "https://example.com"), response=mock_get.return_value)
        )

        with pytest.raises(httpx.HTTPStatusError):
            scrape_announcements_for_year("BHP", 2024)

    @patch("app.analysis.announcement_scraper.httpx.get")
    def test_network_error_propagates(self, mock_get: MagicMock) -> None:
        from app.analysis.announcement_scraper import scrape_announcements_for_year

        mock_get.side_effect = httpx.ConnectError("Connection refused")

        with pytest.raises(httpx.ConnectError):
            scrape_announcements_for_year("BHP", 2024)


class TestFilterAnnouncementsByDateRange:
    """Tests for date range filtering with YYYY-MM-DD format."""

    def test_filter_within_range(self) -> None:
        announcements = [
            Announcement(ticker="BHP", date="2024-01-15", time="09:30", headline="A"),
            Announcement(ticker="BHP", date="2024-06-15", time="15:45", headline="B"),
            Announcement(ticker="BHP", date="2024-12-01", time="10:00", headline="C"),
        ]
        start = datetime(2024, 3, 1)
        end = datetime(2024, 9, 30)

        filtered = filter_announcements_by_date_range(announcements, start, end)

        assert len(filtered) == 1
        assert filtered[0].headline == "B"

    def test_filter_inclusive_boundaries(self) -> None:
        announcements = [
            Announcement(ticker="BHP", date="2024-01-01", time="09:00", headline="Start"),
            Announcement(ticker="BHP", date="2024-12-31", time="17:00", headline="End"),
        ]
        start = datetime(2024, 1, 1)
        end = datetime(2024, 12, 31)

        filtered = filter_announcements_by_date_range(announcements, start, end)

        assert len(filtered) == 2

    def test_filter_empty(self) -> None:
        filtered = filter_announcements_by_date_range([], datetime(2024, 1, 1), datetime(2024, 12, 31))
        assert filtered == []


class TestAnnouncementScraperGetAnnouncements:
    """Tests for AnnouncementScraper.get_announcements returning AnnouncementResult."""

    @patch("app.analysis.announcement_scraper.scrape_announcements_for_year")
    def test_success_result(self, mock_scrape: MagicMock) -> None:
        mock_scrape.return_value = [
            Announcement(ticker="BHP", date="2024-06-15", time="15:45", headline="Q Report"),
        ]

        scraper = AnnouncementScraper()
        result = scraper.get_announcements("bhp", datetime(2024, 1, 1), datetime(2024, 12, 31))

        assert isinstance(result, AnnouncementResult)
        assert result.success is True
        assert result.error is None
        assert result.ticker == "BHP"
        assert result.count == 1
        assert result.period_start == "2024-01-01"
        assert result.period_end == "2024-12-31"

    @patch("app.analysis.announcement_scraper.scrape_announcements_for_year")
    def test_zero_matches_is_success(self, mock_scrape: MagicMock) -> None:
        mock_scrape.return_value = []

        scraper = AnnouncementScraper()
        result = scraper.get_announcements("XYZ", datetime(2024, 1, 1), datetime(2024, 1, 31))

        assert result.success is True
        assert result.count == 0
        assert result.announcements == []

    @patch("app.analysis.announcement_scraper.scrape_announcements_for_year")
    def test_http_failure_returns_error(self, mock_scrape: MagicMock) -> None:
        mock_scrape.side_effect = httpx.HTTPStatusError(
            "503",
            request=httpx.Request("GET", "https://example.com"),
            response=httpx.Response(503, request=httpx.Request("GET", "https://example.com")),
        )

        scraper = AnnouncementScraper()
        result = scraper.get_announcements("BHP", datetime(2024, 1, 1), datetime(2024, 12, 31))

        assert result.success is False
        assert result.error is not None
        assert "failed" in result.error.lower()
        assert result.count == 0

    @patch("app.analysis.announcement_scraper.scrape_announcements_for_year")
    def test_network_failure_returns_error(self, mock_scrape: MagicMock) -> None:
        mock_scrape.side_effect = httpx.ConnectError("Connection refused")

        scraper = AnnouncementScraper()
        result = scraper.get_announcements("BHP", datetime(2024, 1, 1), datetime(2024, 12, 31))

        assert result.success is False
        assert result.error is not None

    @patch("app.analysis.announcement_scraper.scrape_announcements_for_year")
    def test_ticker_uppercased(self, mock_scrape: MagicMock) -> None:
        mock_scrape.return_value = [
            Announcement(ticker="BHP", date="2024-06-15", time="09:00", headline="Test"),
        ]

        scraper = AnnouncementScraper()
        result = scraper.get_announcements("bhp", datetime(2024, 1, 1), datetime(2024, 12, 31))

        assert result.ticker == "BHP"
        assert result.announcements[0].ticker == "BHP"

    @patch("app.analysis.announcement_scraper.scrape_announcements_for_year")
    def test_results_sorted_by_date_desc(self, mock_scrape: MagicMock) -> None:
        mock_scrape.return_value = [
            Announcement(ticker="BHP", date="2024-01-15", time="09:00", headline="Old"),
            Announcement(ticker="BHP", date="2024-06-15", time="15:45", headline="New"),
            Announcement(ticker="BHP", date="2024-03-01", time="10:00", headline="Mid"),
        ]

        scraper = AnnouncementScraper()
        result = scraper.get_announcements("BHP", datetime(2024, 1, 1), datetime(2024, 12, 31))

        assert result.announcements[0].headline == "New"
        assert result.announcements[1].headline == "Mid"
        assert result.announcements[2].headline == "Old"

    @patch("app.analysis.announcement_scraper.scrape_announcements_for_year")
    def test_cross_year_query(self, mock_scrape: MagicMock) -> None:
        mock_scrape.return_value = [
            Announcement(ticker="BHP", date="2023-06-15", time="09:00", headline="2023"),
            Announcement(ticker="BHP", date="2024-01-15", time="10:00", headline="2024"),
        ]

        scraper = AnnouncementScraper()
        result = scraper.get_announcements("BHP", datetime(2023, 7, 1), datetime(2024, 6, 30))

        assert mock_scrape.call_count == 2
        calls = mock_scrape.call_args_list
        assert calls[0][1].get("year", calls[0][0][1] if len(calls[0][0]) > 1 else None) == 2023 or calls[0][0][1] == 2023
        assert result.success is True

    @patch("app.analysis.announcement_scraper.scrape_announcements_for_year")
    def test_partial_year_failure_still_succeeds(self, mock_scrape: MagicMock) -> None:
        """If one year fails but another succeeds, result is still success with partial data."""
        call_count = 0

        def side_effect(ticker: str, year: int, timeout: int = 30) -> list[Announcement]:
            nonlocal call_count
            call_count += 1
            if year == 2023:
                raise httpx.HTTPStatusError(
                    "500",
                    request=httpx.Request("GET", "https://example.com"),
                    response=httpx.Response(500, request=httpx.Request("GET", "https://example.com")),
                )
            return [Announcement(ticker="BHP", date="2024-06-15", time="09:00", headline="2024 data")]

        mock_scrape.side_effect = side_effect

        scraper = AnnouncementScraper()
        result = scraper.get_announcements("BHP", datetime(2023, 7, 1), datetime(2024, 6, 30))

        assert result.success is True
        assert result.count == 1
        assert result.announcements[0].headline == "2024 data"


class TestParseDateRange:
    """Tests for AnnouncementScraper.parse_date_range."""

    def setup_method(self) -> None:
        self.scraper = AnnouncementScraper()
        self.ref = datetime(2024, 6, 15)

    def test_year_only(self) -> None:
        start, end = self.scraper.parse_date_range("2024", self.ref)
        assert start == datetime(2024, 1, 1)
        assert end == datetime(2024, 12, 31)

    def test_year_month(self) -> None:
        start, end = self.scraper.parse_date_range("2024-03", self.ref)
        assert start == datetime(2024, 3, 1)
        assert end == datetime(2024, 3, 31)

    def test_year_month_december(self) -> None:
        start, end = self.scraper.parse_date_range("2024-12", self.ref)
        assert start == datetime(2024, 12, 1)
        assert end == datetime(2024, 12, 31)

    def test_exact_range(self) -> None:
        start, end = self.scraper.parse_date_range("2024-03-01 to 2024-03-31", self.ref)
        assert start == datetime(2024, 3, 1)
        assert end == datetime(2024, 3, 31)

    def test_1m(self) -> None:
        start, end = self.scraper.parse_date_range("1M", self.ref)
        assert end == self.ref
        assert start == self.ref - timedelta(days=30)

    def test_3m(self) -> None:
        start, end = self.scraper.parse_date_range("3M", self.ref)
        assert end == self.ref
        assert start == self.ref - timedelta(days=90)

    def test_6m(self) -> None:
        start, end = self.scraper.parse_date_range("6M", self.ref)
        assert end == self.ref
        assert start == self.ref - timedelta(days=180)

    def test_1y(self) -> None:
        start, end = self.scraper.parse_date_range("1Y", self.ref)
        assert end == self.ref
        assert start == self.ref - timedelta(days=365)

    def test_unknown_period_raises(self) -> None:
        with pytest.raises(ValueError, match="Unknown period format"):
            self.scraper.parse_date_range("invalid", self.ref)

    def test_default_reference_date(self) -> None:
        start, end = self.scraper.parse_date_range("1M")
        expected_end = datetime.now()
        assert abs((end - expected_end).total_seconds()) < 5
