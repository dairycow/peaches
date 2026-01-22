"""Announcement scraper for ASX company announcements."""

from datetime import datetime, timedelta

import requests
from bs4 import BeautifulSoup

ASX_BASE_URL = "https://www.asx.com.au"


def normalize_date(date_str: str) -> str:
    """Convert date from DD/MM/YYYY format to YYYYMMDD."""
    if not date_str or "/" not in date_str:
        return ""

    try:
        day, month, year = date_str.strip().split("/")
        return f"{year}{month.zfill(2)}{day.zfill(2)}"
    except ValueError:
        return ""


def normalize_time(time_str: str) -> int:
    """Convert to 24-hour format."""
    try:
        if "pm" in time_str:
            hour, minute = time_str.replace(" pm", "").split(":")
            hour = int(hour)
            if hour != 12:
                hour += 12
        else:
            hour, minute = time_str.replace(" am", "").split(":")
            hour = int(hour)
            if hour == 12:
                hour = 0
        return int(f"{hour:02d}{minute}")
    except Exception:
        return 0


def extract_page_count(cell) -> int:
    """Extract page count from PDF link cell."""
    page_span = cell.find("span", class_="page")
    page_text = page_span.get_text().strip()
    page_number = page_text.split()[0]
    return int(page_number)


def parse_row(cells) -> dict | None:
    """Extract announcement details from table row."""
    pdf_href = cells[2].find("a").get("href")

    if not pdf_href:
        return None

    return {
        "date": normalize_date(cells[0].get_text().split("\n")[1].strip()),
        "time": normalize_time(cells[0].get_text().split("\n")[2].strip()),
        "headline": cells[2].get_text().split("\n")[2].strip(),
        "price_sensitive": bool(cells[1].find("img", class_="pricesens")),
        "pages": extract_page_count(cells[2]),
    }


def scrape_announcements_for_year(ticker: str, year: int, timeout: int = 30) -> list[dict]:
    """Scrape announcements for a given ticker and year.

    Args:
        ticker: ASX ticker symbol
        year: Year to scrape
        timeout: Request timeout in seconds

    Returns:
        List of announcement dictionaries

    """
    url = f"{ASX_BASE_URL}/asx/v2/statistics/announcements.do?by=asxCode&asxCode={ticker}&timeframe=Y&year={year}"

    try:
        response = requests.get(url, timeout=timeout)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")
        table = soup.select("#content > div > announcement_data > table")

        if not table:
            return []

        announcements = table[0].select("tr")[1:]
        results = []

        for row in announcements:
            cells = row.select("td")
            if len(cells) < 3:
                continue

            announcement = parse_row(cells)
            if announcement and announcement["date"]:
                results.append(announcement)

        return results
    except Exception:
        return []


def filter_announcements_by_date_range(
    announcements: list[dict], start_date: datetime, end_date: datetime
) -> list[dict]:
    """Filter announcements to only those within date range.

    Args:
        announcements: List of announcements
        start_date: Start date for filtering
        end_date: End date for filtering

    Returns:
        Filtered list of announcements

    """
    start_date_str = start_date.strftime("%Y%m%d")
    end_date_str = end_date.strftime("%Y%m%d")

    return [ann for ann in announcements if start_date_str <= ann["date"] <= end_date_str]


class AnnouncementScraper:
    """Scrapes and retrieves ASX company announcements."""

    def __init__(self, timeout: int = 30):
        """Initialize AnnouncementScraper.

        Args:
            timeout: Request timeout in seconds

        """
        self.timeout = timeout

    def get_announcements(
        self, ticker: str, start_date: datetime, end_date: datetime
    ) -> list[dict]:
        """Get announcements for a ticker within date range.

        Args:
            ticker: ASX ticker symbol
            start_date: Start date for filtering
            end_date: End date for filtering

        Returns:
            List of announcement dictionaries with date, time, headline, price_sensitive, pages

        """
        ticker = ticker.upper()
        results = []

        start_year = start_date.year
        end_year = end_date.year

        for year in range(start_year, end_year + 1):
            year_announcements = scrape_announcements_for_year(ticker, year, timeout=self.timeout)
            results.extend(year_announcements)

        filtered_results = filter_announcements_by_date_range(results, start_date, end_date)
        filtered_results.sort(key=lambda x: x["date"], reverse=True)

        return filtered_results

    def parse_date_range(
        self, period: str, reference_date: datetime | None = None
    ) -> tuple[datetime, datetime]:
        """Parse period string into date range.

        Supported formats:
        - "YYYY" (e.g., "2025")
        - "YYYY-MM" (e.g., "2024-03")
        - "YYYY-MM-DD to YYYY-MM-DD" (e.g., "2024-03-01 to 2024-03-31")
        - "1M", "3M", "6M", "1Y" (last X months/years from reference)

        Args:
            period: Period string
            reference_date: Reference date for relative periods

        Returns:
            Tuple of (start_date, end_date)

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
