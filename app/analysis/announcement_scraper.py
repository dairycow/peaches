"""Announcement scraper for ASX company announcements.

Historical scraper — fetches announcements for a single ticker over a date range.
Uses sync httpx (CLI-only consumer). Async wrapper via asyncio.to_thread() if needed later.

Known limitation: historical endpoint does not provide announcement_id or pdf_url.
These fields are left as empty strings — downstream consumers should not treat empty as a bug.
"""

import contextlib
from datetime import datetime, timedelta

import httpx
from bs4 import BeautifulSoup
from loguru import logger

from app.analysis.models import Announcement, AnnouncementResult
from app.analysis.parsing import extract_page_count, normalise_date, normalise_time

ASX_BASE_URL = "https://www.asx.com.au"


def _parse_row(cells: list, ticker: str) -> Announcement | None:
    """Extract announcement details from a 3-cell historical table row.

    Historical rows: cells[0] = date/time, cells[1] = price-sensitive icon,
    cells[2] = headline/pages. No ticker column (ticker is the query input).

    Returns None if the row has no valid date or no PDF link.
    """
    try:
        pdf_href = cells[2].find("a").get("href")
        if not pdf_href:
            return None

        date_time_text = cells[0].get_text()
        lines = [line.strip() for line in date_time_text.split("\n") if line.strip()]

        date_str = ""
        time_str = "00:00"
        for line in lines:
            if "/" in line and not date_str:
                date_str = normalise_date(line)
            elif (("am" in line.lower() or "pm" in line.lower()) and ":" in line) and time_str == "00:00":
                time_str = normalise_time(line)

        if not date_str:
            return None

        headline = ""
        with contextlib.suppress(IndexError):
            headline = cells[2].get_text().split("\n")[2].strip()

        price_sensitive = bool(cells[1].find("img", class_="pricesens"))
        pages = extract_page_count(cells[2])

        return Announcement(
            ticker=ticker,
            date=date_str,
            time=time_str,
            headline=headline,
            price_sensitive=price_sensitive,
            pages=pages,
        )
    except Exception:
        logger.warning("Failed to parse historical announcement row, skipping")
        return None


def scrape_announcements_for_year(ticker: str, year: int, timeout: int = 30) -> list[Announcement]:
    """Scrape announcements for a given ticker and year.

    Per-row error handling: malformed rows are skipped with a warning,
    other rows continue processing. Network/HTTP failures propagate upward
    so the caller can set success=False.
    """
    url = (
        f"{ASX_BASE_URL}/asx/v2/statistics/announcements.do"
        f"?by=asxCode&asxCode={ticker}&timeframe=Y&year={year}"
    )

    response = httpx.get(url, timeout=timeout)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")
    table = soup.select("#content > div > announcement_data > table")

    if not table:
        return []

    announcements = table[0].select("tr")[1:]
    results: list[Announcement] = []

    for row in announcements:
        cells = row.select("td")
        if len(cells) < 3:
            continue

        announcement = _parse_row(cells, ticker)
        if announcement is not None:
            results.append(announcement)

    return results


def filter_announcements_by_date_range(
    announcements: list[Announcement], start_date: datetime, end_date: datetime
) -> list[Announcement]:
    """Filter announcements to only those within date range.

    Uses YYYY-MM-DD format (scanner contract) for comparison.
    """
    start_date_str = start_date.strftime("%Y-%m-%d")
    end_date_str = end_date.strftime("%Y-%m-%d")

    return [ann for ann in announcements if start_date_str <= ann.date <= end_date_str]


class AnnouncementScraper:
    """Scrapes and retrieves ASX company announcements."""

    def __init__(self, timeout: int = 30):
        self.timeout = timeout

    def get_announcements(
        self, ticker: str, start_date: datetime, end_date: datetime
    ) -> AnnouncementResult:
        """Get announcements for a ticker within date range.

        Returns AnnouncementResult with success=True on successful scrape
        (even if zero matches). Returns success=False only on network/HTTP failure.
        """
        ticker = ticker.upper()
        results: list[Announcement] = []
        years_requested = 0
        years_failed = 0

        try:
            start_year = start_date.year
            end_year = end_date.year

            for year in range(start_year, end_year + 1):
                years_requested += 1
                try:
                    year_announcements = scrape_announcements_for_year(
                        ticker, year, timeout=self.timeout
                    )
                    results.extend(year_announcements)
                except httpx.HTTPStatusError as e:
                    years_failed += 1
                    logger.warning(f"HTTP error scraping {ticker} for year {year}: {e}")
                except httpx.RequestError as e:
                    years_failed += 1
                    logger.warning(f"Request error scraping {ticker} for year {year}: {e}")

            filtered_results = filter_announcements_by_date_range(results, start_date, end_date)
            filtered_results.sort(key=lambda x: (x.date, x.time), reverse=True)

            all_years_failed = years_requested > 0 and years_failed == years_requested
            if all_years_failed:
                return AnnouncementResult(
                    ticker=ticker,
                    period_start=start_date.strftime("%Y-%m-%d"),
                    period_end=end_date.strftime("%Y-%m-%d"),
                    count=0,
                    success=False,
                    error=f"All {years_requested} year(s) failed to scrape",
                    announcements=[],
                )

            return AnnouncementResult(
                ticker=ticker,
                period_start=start_date.strftime("%Y-%m-%d"),
                period_end=end_date.strftime("%Y-%m-%d"),
                count=len(filtered_results),
                success=True,
                announcements=filtered_results,
            )
        except Exception as e:
            logger.error(f"Unexpected error scraping announcements for {ticker}: {e}")
            return AnnouncementResult(
                ticker=ticker,
                period_start=start_date.strftime("%Y-%m-%d"),
                period_end=end_date.strftime("%Y-%m-%d"),
                count=0,
                success=False,
                error=str(e),
                announcements=[],
            )

    def parse_date_range(
        self, period: str, reference_date: datetime | None = None
    ) -> tuple[datetime, datetime]:
        """Parse period string into date range.

        Supported formats:
        - "YYYY" (e.g., "2025")
        - "YYYY-MM" (e.g., "2024-03")
        - "YYYY-MM-DD to YYYY-MM-DD" (e.g., "2024-03-01 to 2024-03-31")
        - "1M", "3M", "6M", "1Y" (last X months/years from reference)
        """
        if reference_date is None:
            reference_date = datetime.now()

        period = period.strip()

        if period.isdigit() and len(period) == 4:
            start_date = datetime(int(period), 1, 1)
            end_date = datetime(int(period), 12, 31)
            return start_date, end_date

        if " to " in period.lower():
            parts = period.lower().split(" to ")
            start_date = datetime.strptime(parts[0].strip(), "%Y-%m-%d")
            end_date = datetime.strptime(parts[1].strip(), "%Y-%m-%d")
            return start_date, end_date

        if "-" in period and len(period) == 7:
            year, month = map(int, period.split("-"))
            if month == 12:
                end_date = datetime(year + 1, 1, 1) - timedelta(days=1)
            else:
                end_date = datetime(year, month + 1, 1) - timedelta(days=1)
            start_date = datetime(year, month, 1)
            return start_date, end_date

        if period.upper() == "1M":
            end_date = reference_date
            start_date = reference_date - timedelta(days=30)
        elif period.upper() == "3M":
            end_date = reference_date
            start_date = reference_date - timedelta(days=90)
        elif period.upper() == "6M":
            end_date = reference_date
            start_date = reference_date - timedelta(days=180)
        elif period.upper() == "1Y":
            end_date = reference_date
            start_date = reference_date - timedelta(days=365)
        else:
            raise ValueError(f"Unknown period format: {period}")

        return start_date, end_date
