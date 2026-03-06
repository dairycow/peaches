"""Service for orchestrating announcement gap strategy workflow."""

from __future__ import annotations

from typing import TYPE_CHECKING

from loguru import logger

from app.scanners.asx import ASXPriceSensitiveScanner, ScannerConfig
from app.scanners.gap.announcement_gap_scanner import (
    AnnouncementGapCandidate,
    AnnouncementGapScanner,
)

if TYPE_CHECKING:
    from ibind import IbkrClient

    from app.config import IBKRScannerConfig


class AnnouncementGapStrategyService:
    """Service for orchestrating announcement gap strategy.

    Workflow:
    1. Scan ASX for today's price-sensitive announcements
    2. Filter stocks by gap + 6M high + price criteria
    3. Sample opening ranges for candidates
    4. Trigger trading strategies for qualified candidates

    Uses IBKR for real-time gap data, CoolTrader for historical 6M high.
    """

    def __init__(
        self,
        asx_scanner_config: ScannerConfig,
        ibkr_config: IBKRScannerConfig | None = None,
        min_price: float = 0.20,
        min_gap_pct: float = 0.0,
        lookback_months: int = 6,
    ) -> None:
        """Initialize announcement gap strategy service.

        Args:
            asx_scanner_config: ASX announcement scanner configuration
            ibkr_config: IBKR scanner configuration for gap data (optional)
            min_price: Minimum stock price threshold
            min_gap_pct: Minimum gap percentage
            lookback_months: Lookback period for high calculation
        """
        self.asx_scanner = ASXPriceSensitiveScanner(asx_scanner_config)
        self.ibkr_config = ibkr_config
        self._ibkr_client: IbkrClient | None = None

        self.min_price = min_price
        self.min_gap_pct = min_gap_pct
        self.lookback_months = lookback_months

    async def connect_ibkr(self) -> IbkrClient | None:
        """Connect to IBKR if configured.

        Returns:
            IbkrClient instance if connected, None otherwise
        """
        if self._ibkr_client:
            return self._ibkr_client

        if not self.ibkr_config or not self.ibkr_config.enabled:
            logger.info("IBKR not configured for announcement gap service")
            return None

        try:
            from ibind import IbkrClient
            from ibind.oauth.oauth1a import OAuth1aConfig

            oauth_config = OAuth1aConfig(
                consumer_key=self.ibkr_config.oauth_consumer_key,
                access_token=self.ibkr_config.oauth_access_token,
                access_token_secret=self.ibkr_config.oauth_access_token_secret,
                dh_prime=self.ibkr_config.oauth_dh_prime,
                encryption_key_fp=self.ibkr_config.encryption_key_path,
                signature_key_fp=self.ibkr_config.signature_key_path,
                realm=self.ibkr_config.realm,
                init_oauth=False,
                maintain_oauth=False,
                init_brokerage_session=False,
            )

            self._ibkr_client = IbkrClient(
                use_oauth=True,
                oauth_config=oauth_config,
                timeout=self.ibkr_config.timeout,
            )

            self._ibkr_client.oauth_init(
                maintain_oauth=False,
                init_brokerage_session=False,
            )

            try:
                self._ibkr_client.initialize_brokerage_session(compete=True)
            except Exception as e:
                logger.warning(f"IBKR brokerage session init note: {e}")

            logger.info("Announcement gap service connected to IBKR")
            return self._ibkr_client

        except Exception as e:
            logger.error(f"Failed to connect to IBKR: {e}")
            self._ibkr_client = None
            return None

    async def disconnect_ibkr(self) -> None:
        """Disconnect from IBKR."""
        if not self._ibkr_client:
            return

        try:
            self._ibkr_client.stop_tickler(timeout=5)
            self._ibkr_client.close()
        except Exception as e:
            logger.warning(f"Error disconnecting IBKR: {e}")
        finally:
            self._ibkr_client = None

        logger.info("Announcement gap service disconnected from IBKR")

    async def run_daily_scan(self) -> list[AnnouncementGapCandidate]:
        """Run complete daily scan workflow.

        Returns:
            List of qualified announcement gap candidates
        """
        from datetime import datetime

        logger.info("Starting announcement gap strategy daily scan")

        ibkr_client = await self.connect_ibkr()

        scan_result = await self.asx_scanner.fetch_announcements()

        if not scan_result.success:
            logger.error(f"Failed to fetch announcements: {scan_result.error}")
            return []

        if not scan_result.announcements:
            logger.info("No price-sensitive announcements found")
            return []

        logger.info(f"Found {len(scan_result.announcements)} price-sensitive announcements")

        announcement_symbols = [
            (ann["ticker"], ann["headline"], datetime.fromisoformat(f"{ann['date']} {ann['time']}"))
            for ann in scan_result.announcements
        ]

        scanner = AnnouncementGapScanner(ibkr_client=ibkr_client)

        candidates = await scanner.scan_candidates(
            announcement_symbols,
            min_price=self.min_price,
            min_gap_pct=self.min_gap_pct,
            lookback_months=self.lookback_months,
        )

        return candidates

    async def scan_and_sample_opening_ranges(
        self,
    ) -> tuple[list[AnnouncementGapCandidate], dict[str, float]]:
        """Scan candidates and sample opening ranges.

        Returns:
            Tuple of (candidates, opening_range_highs)
        """
        candidates = await self.run_daily_scan()

        if not candidates:
            return [], {}

        ibkr_client = await self.connect_ibkr()
        scanner = AnnouncementGapScanner(ibkr_client=ibkr_client)
        opening_ranges = await scanner.sample_opening_ranges(candidates)

        return candidates, opening_ranges
