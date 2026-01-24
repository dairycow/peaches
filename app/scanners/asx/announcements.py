"""ASX price-sensitive announcements scanner."""

import asyncio
import contextlib
from dataclasses import dataclass
from typing import TypedDict

import aiohttp
from aiohttp import ClientTimeout
from bs4 import BeautifulSoup
from loguru import logger
from tenacity import retry, stop_after_attempt, wait_exponential

from app.scanners.base import ScannerBase, ScanResult


class Announcement(TypedDict):
    """ASX announcement data structure."""

    ticker: str
    headline: str
    date: str
    time: str
    price_sensitive: bool
    pages: int
    announcement_id: str
    pdf_url: str


@dataclass
class ScannerConfig:
    """Configuration for scanner."""

    url: str
    timeout: int
    exclude_tickers: list[str]
    min_ticker_length: int
    max_ticker_length: int


@dataclass
class ASXScanResult:
    """Result from scanning announcements."""

    announcements: list[Announcement]
    success: bool
    error: str | None


class ASXAnnouncementScanner(ScannerBase):
    """Scanner for ASX announcements."""

    def __init__(self, config: ScannerConfig) -> None:
        """Initialize scanner with configuration.

        Args:
            config: Scanner configuration
        """
        self.config = config

    @property
    def name(self) -> str:
        """Scanner identifier."""
        return "asx_announcements"

    async def execute(self) -> ScanResult:
        """Execute the scan operation.

        Returns:
            ScanResult with results or error details
        """
        asx_result = await self.fetch_announcements()

        return ScanResult(
            success=asx_result.success,
            message=f"Fetched {len(asx_result.announcements)} announcements",
            data=[dict(a) for a in asx_result.announcements],
            error=asx_result.error,
        )

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
    )
    async def fetch_announcements(self) -> ASXScanResult:
        """Fetch ASX announcements.

        Returns:
            ASXScanResult with announcements or error
        """
        logger.info(f"Fetching ASX announcements from {self.config.url}")

        try:
            announcements = await self.scrape_announcements()

            logger.info(f"Found {len(announcements)} valid announcements")
            return ASXScanResult(announcements=announcements, success=True, error=None)

        except Exception as e:
            logger.error(f"Error fetching ASX announcements: {e}")
            return ASXScanResult(announcements=[], success=False, error=str(e))

    async def scrape_announcements(self, fetch_pdf_urls: bool = False) -> list[Announcement]:
        """Scrape ASX announcements from today.

        Args:
            fetch_pdf_urls: Whether to fetch direct PDF URLs for announcements

        Returns:
            List of announcements
        """
        logger.info("Scraping ASX announcements")

        asx_base = "https://www.asx.com.au"

        try:
            async with (
                aiohttp.ClientSession() as session,
                session.get(
                    self.config.url, timeout=ClientTimeout(total=self.config.timeout)
                ) as response,
            ):
                response.raise_for_status()
                html = await response.text()
        except Exception as e:
            logger.error(f"Failed to scrape announcements: {e}")
            return []

        soup = BeautifulSoup(html, "html.parser")
        all_rows = soup.select("table tr")[1:]

        logger.debug(f"Total rows: {len(all_rows)}")

        announcements: list[Announcement] = []
        for row in all_rows:
            cells = row.find_all("td")
            if len(cells) == 4 and (ann := self._parse_row(cells, asx_base)):
                announcements.append(ann)

        logger.info(f"Found {len(announcements)} announcements")

        if announcements and fetch_pdf_urls:
            announcements = await self._fetch_pdf_urls(announcements, 5, self.config.timeout)

        return announcements

    def _parse_row(self, cells: list, asx_base: str) -> Announcement | None:
        """Parse a single announcement row."""
        try:
            ticker = cells[0].get_text(strip=True)

            datetime_text = cells[1].get_text()
            date_str = self._normalize_date(datetime_text.split("\n")[1].strip())
            time_str = self._normalize_time(datetime_text.split("\n")[2].strip())

            price_sensitive = bool(cells[2].find("img", class_="pricesens"))

            pdf_link = cells[3].find("a")
            if not pdf_link or not pdf_link.get("href"):
                return None

            pdf_href = pdf_link["href"]
            announcement_id = pdf_href.split("idsId=")[1] if "idsId=" in pdf_href else ""

            cell_lines = cells[3].get_text().split("\n")
            headline = (
                cell_lines[2].strip() if len(cell_lines) > 2 else pdf_link.get_text(strip=True)
            )

            page_span = cells[3].find("span", class_="page")
            pages = 1
            if page_span:
                with contextlib.suppress(ValueError, IndexError):
                    pages = int(page_span.get_text().strip().split()[0])

            return Announcement(
                ticker=ticker,
                headline=headline,
                date=date_str,
                time=time_str,
                price_sensitive=price_sensitive,
                pages=pages,
                announcement_id=announcement_id,
                pdf_url=asx_base + pdf_href,
            )

        except Exception as e:
            logger.warning(f"Failed to parse row: {e}")
            return None

    def _normalize_date(self, date_str: str) -> str:
        """Convert DD/MM/YYYY to YYYY-MM-DD."""
        try:
            day, month, year = date_str.strip().split("/")
            return f"{year}-{month.zfill(2)}-{day.zfill(2)}"
        except ValueError:
            return ""

    def _normalize_time(self, time_str: str) -> str:
        """Convert to 24-hour HH:MM format."""
        try:
            time_str = time_str.lower().strip()
            parts = time_str.replace(" pm", "").replace(" am", "").split(":")
            hour = int(parts[0])
            minute = int(parts[1])

            if "pm" in time_str and hour != 12:
                hour += 12
            elif "am" in time_str and hour == 12:
                hour = 0

            return f"{hour:02d}:{minute:02d}"
        except (ValueError, IndexError):
            return "00:00"

    async def _fetch_pdf_urls(
        self, announcements: list[Announcement], max_concurrent: int, timeout: int
    ) -> list[Announcement]:
        """Fetch direct PDF URLs for all announcements concurrently."""
        logger.info(f"Fetching {len(announcements)} PDF URLs with max_concurrent={max_concurrent}")

        semaphore = asyncio.Semaphore(max_concurrent)

        async def fetch_one(ann: Announcement) -> Announcement:
            async with semaphore:
                try:
                    async with (
                        aiohttp.ClientSession() as session,
                        session.get(
                            ann["pdf_url"], timeout=ClientTimeout(total=timeout)
                        ) as response,
                    ):
                        response.raise_for_status()
                        html = await response.text()

                    soup = BeautifulSoup(html, "html.parser")
                    pdf_input = soup.find("input", {"name": "pdfURL"})

                    if pdf_input and pdf_input.get("value"):
                        ann["pdf_url"] = str(pdf_input["value"])
                        logger.debug(f"Got PDF URL for {ann['ticker']}")
                    else:
                        logger.warning(f"No PDF URL found for {ann['ticker']}")

                except Exception as e:
                    logger.error(f"Failed to fetch PDF URL for {ann['ticker']}: {e}")

                return ann

        return await asyncio.gather(*[fetch_one(ann) for ann in announcements])


class ASXPriceSensitiveScanner(ScannerBase):
    """Scanner for ASX price-sensitive announcements."""

    def __init__(self, config: ScannerConfig) -> None:
        """Initialize scanner with configuration.

        Args:
            config: Scanner configuration
        """
        self.config = config
        self.announcement_scanner = ASXAnnouncementScanner(config)

    @property
    def name(self) -> str:
        """Scanner identifier."""
        return "asx_price_sensitive"

    async def execute(self) -> ScanResult:
        """Execute the scan operation.

        Returns:
            ScanResult with results or error details
        """
        asx_result = await self.fetch_announcements()

        return ScanResult(
            success=asx_result.success,
            message=f"Found {len(asx_result.announcements)} price-sensitive announcements",
            data=[dict(a) for a in asx_result.announcements],
            error=asx_result.error,
        )

    async def fetch_announcements(self) -> ASXScanResult:
        """Fetch price-sensitive announcements.

        Returns:
            ASXScanResult with price-sensitive announcements or error
        """
        asx_result = await self.announcement_scanner.fetch_announcements()

        if not asx_result.success:
            return asx_result

        return self._filter_price_sensitive(asx_result)

    def _filter_price_sensitive(self, result: ASXScanResult) -> ASXScanResult:
        """Filter price-sensitive announcements from scan result.

        Args:
            result: ASXScanResult to filter

        Returns:
            ASXScanResult with only price-sensitive announcements
        """
        filtered = [a for a in result.announcements if self._is_price_sensitive(a)]

        logger.info(f"Filtered to {len(filtered)} price-sensitive announcements")

        return ASXScanResult(
            announcements=filtered,
            success=True,
            error=None,
        )

    def _is_price_sensitive(self, announcement: Announcement) -> bool:
        """Check if announcement is price-sensitive.

        Args:
            announcement: Announcement to check

        Returns:
            True if announcement is price-sensitive
        """
        return announcement["price_sensitive"]
