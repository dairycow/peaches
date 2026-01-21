"""CoolTrader downloader for ASX historical data."""

from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from httpx import AsyncClient
from loguru import logger
from tenacity import retry, stop_after_attempt, wait_exponential

from app.config import config


class CoolTraderDownloader:
    """CoolTrader EOD data downloader."""

    def __init__(self) -> None:
        """Initialize CoolTrader downloader."""
        self.client: AsyncClient | None = None
        self._authenticated = False
        self.base_url = config.cooltrader.base_url
        self.username = config.cooltrader.username
        self.password = config.cooltrader.password
        self.download_dir = Path(config.historical_data.csv_dir)

    async def _login(self) -> None:
        """Login to CoolTrader.

        Raises:
            ConnectionError: If login fails
        """
        if self._authenticated:
            return

        try:
            self.client = AsyncClient(
                timeout=30,
                follow_redirects=True,
            )

            login_url = "https://data.cooltrader.com.au/amember/login"
            login_data = {
                "amember_login": self.username,
                "amember_pass": self.password,
            }

            response = await self.client.post(login_url, data=login_data)
            response.raise_for_status()

            self._authenticated = True
            logger.info("Successfully logged in to CoolTrader")

        except Exception as e:
            logger.error(f"Failed to login to CoolTrader: {e}")
            raise ConnectionError(f"CoolTrader login failed: {e}") from None

    def _get_download_url(self, date_obj: date) -> str:
        """Generate download URL for specific date.

        Args:
            date_obj: Date to download

        Returns:
            Download URL string
        """
        date_str = date_obj.strftime("%Y%m%d")
        return f"https://data.cooltrader.com.au/amember/eodfiles/nextday/csv/{date_str}.csv"

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True,
    )
    async def download_csv(self, date_obj: date, output_path: Path | None = None) -> Path:
        """Download CSV file for specific date.

        Args:
            date_obj: Date to download
            output_path: Output file path (optional, auto-generated if not provided)

        Returns:
            Path to downloaded file

        Raises:
            ConnectionError: If download fails
        """
        if not self._authenticated:
            await self._login()

        if output_path is None:
            output_path = self.download_dir / f"{date_obj.strftime('%Y%m%d')}.csv"

        output_path.parent.mkdir(parents=True, exist_ok=True)

        url = self._get_download_url(date_obj)

        try:
            if self.client is None:
                raise RuntimeError("HTTP client not initialized")
            response = await self.client.get(url)
            response.raise_for_status()

            with open(output_path, "wb") as f:
                f.write(response.content)

            logger.info(f"Downloaded CoolTrader data for {date_obj} to {output_path}")
            return output_path

        except Exception as e:
            logger.error(f"Failed to download CoolTrader data for {date_obj}: {e}")
            raise ConnectionError(f"Download failed for {date_obj}: {e}") from None

    async def download_yesterday(self) -> Path:
        """Download CSV file for yesterday.

        Returns:
            Path to downloaded file
        """
        sydney_now = datetime.now(ZoneInfo("Australia/Sydney"))
        yesterday = sydney_now.date() - timedelta(days=1)
        return await self.download_csv(yesterday)

    async def close(self) -> None:
        """Close HTTP client."""
        if self.client:
            await self.client.aclose()
            self.client = None
            self._authenticated = False
            logger.info("Closed CoolTrader HTTP client")


def create_downloader() -> CoolTraderDownloader:
    """Create CoolTrader downloader instance.

    Returns:
        CoolTraderDownloader instance
    """
    return CoolTraderDownloader()
