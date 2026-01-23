"""ASX price-sensitive announcements scanner."""

from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING

from loguru import logger
from tenacity import retry, stop_after_attempt, wait_exponential

from app.models.announcement import Announcement
from app.scanners.base import ScannerBase, ScanResult

if TYPE_CHECKING:
    pass


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


class ASXPriceSensitiveScanner(ScannerBase):
    """Scanner for ASX price-sensitive announcements."""

    def __init__(self, config: ScannerConfig) -> None:
        """Initialize scanner with configuration.

        Args:
            config: Scanner configuration
        """
        self.config = config

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
            message=f"Fetched {len(asx_result.announcements)} announcements",
            data=[a.__dict__ for a in asx_result.announcements],
            error=asx_result.error,
        )

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
    )
    async def fetch_announcements(self) -> ASXScanResult:
        """Fetch ASX price-sensitive announcements.

        Returns:
            ASXScanResult with announcements or error
        """
        try:
            import httpx
            from bs4 import BeautifulSoup

            logger.info(f"Fetching ASX announcements from {self.config.url}")

            async with httpx.AsyncClient(timeout=self.config.timeout) as client:
                response = await client.get(self.config.url)
                response.raise_for_status()

            soup = BeautifulSoup(response.text, "lxml")
            rows = soup.find_all("tr")

            announcements = []

            for row in rows:
                if "pricesens" not in str(row):
                    continue

                cells = row.find_all("td")
                if len(cells) >= 3:
                    ticker = cells[0].get_text(strip=True)
                    headline = cells[1].get_text(strip=True)

                    if not self._validate_ticker(ticker):
                        continue

                    announcements.append(
                        Announcement(
                            ticker=ticker,
                            headline=headline,
                            timestamp=datetime.now().isoformat(),
                            url=None,
                        )
                    )

            logger.info(f"Found {len(announcements)} valid announcements")
            return ASXScanResult(announcements=announcements, success=True, error=None)

        except Exception as e:
            logger.error(f"Error fetching ASX announcements: {e}")
            return ASXScanResult(announcements=[], success=False, error=str(e))

    def _validate_ticker(self, ticker: str) -> bool:
        """Validate ticker format.

        Args:
            ticker: Ticker symbol to validate

        Returns:
            True if ticker is valid, False otherwise
        """
        if not self.config.min_ticker_length <= len(ticker) <= self.config.max_ticker_length:
            return False

        return ticker not in self.config.exclude_tickers
