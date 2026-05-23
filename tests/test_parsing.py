"""Unit tests for shared ASX HTML parsing normalisers.

Verifies that normalisers produce the scanner contract:
  - normalise_date -> YYYY-MM-DD
  - normalise_time -> HH:MM (24hr string)
  - extract_page_count -> int, never throws

Critical contract test: datetime.fromisoformat(f"{date} {time}") must parse
for all valid normaliser outputs, matching the gap strategy at
announcement_gap_strategy_service.py:67.
"""

from datetime import datetime

import pytest
from bs4 import BeautifulSoup, Tag

from app.analysis.parsing import extract_page_count, normalise_date, normalise_time


class TestNormaliseDate:
    """normalise_date must produce YYYY-MM-DD for valid DD/MM/YYYY input."""

    def test_valid_date(self) -> None:
        assert normalise_date("23/05/2026") == "2026-05-23"

    def test_single_digit_day_month(self) -> None:
        assert normalise_date("1/3/2025") == "2025-03-01"

    def test_zero_padded(self) -> None:
        assert normalise_date("01/03/2025") == "2025-03-01"

    def test_empty_string(self) -> None:
        assert normalise_date("") == ""

    def test_none_like_empty(self) -> None:
        assert normalise_date("   ") == ""

    def test_no_slashes(self) -> None:
        assert normalise_date("20260523") == ""

    def test_malformed_date(self) -> None:
        assert normalise_date("not/a/date") == ""

    def test_fromisoformat_roundtrip(self) -> None:
        """Scanner contract: result must parse via datetime.fromisoformat."""
        result = normalise_date("15/06/2024")
        parsed = datetime.fromisoformat(result)
        assert parsed.year == 2024
        assert parsed.month == 6
        assert parsed.day == 15

    def test_fromisoformat_roundtrip_all_formats(self) -> None:
        """Every valid normalise_date output must parse as a date."""
        inputs = ["01/01/2020", "31/12/2025", "15/06/2024", "9/3/2023"]
        for inp in inputs:
            result = normalise_date(inp)
            assert result, f"Expected non-empty for {inp}"
            datetime.fromisoformat(result)


class TestNormaliseTime:
    """normalise_time must produce HH:MM (24hr string) for valid input."""

    def test_am_time(self) -> None:
        assert normalise_time("9:30 am") == "09:30"

    def test_pm_time(self) -> None:
        assert normalise_time("3:45 pm") == "15:45"

    def test_noon(self) -> None:
        assert normalise_time("12:00 pm") == "12:00"

    def test_midnight(self) -> None:
        assert normalise_time("12:00 am") == "00:00"

    def test_leading_zero(self) -> None:
        assert normalise_time("09:05 am") == "09:05"

    def test_evening(self) -> None:
        assert normalise_time("11:59 pm") == "23:59"

    def test_empty_string(self) -> None:
        assert normalise_time("") == "00:00"

    def test_malformed_time(self) -> None:
        assert normalise_time("not a time") == "00:00"

    def test_fromisoformat_roundtrip(self) -> None:
        """Scanner contract: result must parse as HH:MM via fromisoformat."""
        result = normalise_time("3:45 pm")
        combined = f"2024-06-15 {result}"
        parsed = datetime.fromisoformat(combined)
        assert parsed.hour == 15
        assert parsed.minute == 45

    def test_fromisoformat_roundtrip_all_formats(self) -> None:
        """Every valid normalise_time output must parse as time in fromisoformat."""
        inputs = ["9:30 am", "3:45 pm", "12:00 pm", "12:00 am", "11:59 pm"]
        for inp in inputs:
            result = normalise_time(inp)
            combined = f"2024-06-15 {result}"
            datetime.fromisoformat(combined)


class TestCombinedContract:
    """Verify the combined date+time contract matches gap strategy usage."""

    def test_gap_strategy_pattern(self) -> None:
        """announcement_gap_strategy_service.py:67 does:
        datetime.fromisoformat(f"{ann['date']} {ann['time']}")
        This must work for all valid normalised outputs.
        """
        date = normalise_date("23/05/2026")
        time = normalise_time("3:45 pm")
        announcement_time = datetime.fromisoformat(f"{date} {time}")
        assert announcement_time.year == 2026
        assert announcement_time.month == 5
        assert announcement_time.day == 23
        assert announcement_time.hour == 15
        assert announcement_time.minute == 45

    def test_gap_strategy_pattern_am(self) -> None:
        date = normalise_date("01/01/2025")
        time = normalise_time("9:05 am")
        announcement_time = datetime.fromisoformat(f"{date} {time}")
        assert announcement_time.hour == 9
        assert announcement_time.minute == 5

    def test_invalid_date_produces_empty_not_crash(self) -> None:
        """Invalid date -> empty string, not an exception."""
        date = normalise_date("")
        assert date == ""

    def test_invalid_time_produces_default_not_crash(self) -> None:
        """Invalid time -> '00:00', not an exception."""
        time = normalise_time("")
        assert time == "00:00"


class TestExtractPageCount:
    """extract_page_count must return int, never throw, default to 1."""

    def _make_cell(self, html: str) -> Tag:
        soup = BeautifulSoup(f"<td>{html}</td>", "html.parser")
        cell = soup.find("td")
        assert isinstance(cell, Tag)
        return cell

    def test_valid_page_count(self) -> None:
        cell = self._make_cell('<span class="page">3 page(s)</span>')
        assert extract_page_count(cell) == 3

    def test_single_page(self) -> None:
        cell = self._make_cell('<span class="page">1 page(s)</span>')
        assert extract_page_count(cell) == 1

    def test_missing_span(self) -> None:
        cell = self._make_cell("no span here")
        assert extract_page_count(cell) == 1

    def test_junk_text_in_span(self) -> None:
        cell = self._make_cell('<span class="page">not a number</span>')
        assert extract_page_count(cell) == 1

    def test_empty_span(self) -> None:
        cell = self._make_cell('<span class="page"></span>')
        assert extract_page_count(cell) == 1

    def test_large_page_count(self) -> None:
        cell = self._make_cell('<span class="page">150 page(s)</span>')
        assert extract_page_count(cell) == 150
