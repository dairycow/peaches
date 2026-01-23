"""Service for orchestrating announcement gap strategy workflow."""

from datetime import datetime

from loguru import logger

from app.scanners.asx import ASXPriceSensitiveScanner, ScannerConfig
from app.scanners.gap.announcement_gap_scanner import (
    AnnouncementGapCandidate,
    AnnouncementGapScanner,
)


class AnnouncementGapStrategyService:
    """Service for orchestrating announcement gap strategy.

    Workflow:
    1. Scan ASX for today's price-sensitive announcements
    2. Filter stocks by gap + 6M high + price criteria
    3. Sample opening ranges for candidates
    4. Trigger trading strategies for qualified candidates
    """

    def __init__(
        self,
        asx_scanner_config: ScannerConfig,
        min_price: float = 0.20,
        min_gap_pct: float = 0.0,
        lookback_months: int = 6,
    ) -> None:
        """Initialize announcement gap strategy service.

        Args:
            asx_scanner_config: ASX announcement scanner configuration
            min_price: Minimum stock price threshold
            min_gap_pct: Minimum gap percentage
            lookback_months: Lookback period for high calculation
        """
        self.asx_scanner = ASXPriceSensitiveScanner(asx_scanner_config)
        self.announcement_gap_scanner = AnnouncementGapScanner()

        self.min_price = min_price
        self.min_gap_pct = min_gap_pct
        self.lookback_months = lookback_months

    async def run_daily_scan(self) -> list[AnnouncementGapCandidate]:
        """Run complete daily scan workflow.

        Returns:
            List of qualified announcement gap candidates
        """
        logger.info("Starting announcement gap strategy daily scan")

        scan_result = await self.asx_scanner.fetch_announcements()

        if not scan_result.success:
            logger.error(f"Failed to fetch announcements: {scan_result.error}")
            return []

        if not scan_result.announcements:
            logger.info("No price-sensitive announcements found")
            return []

        logger.info(f"Found {len(scan_result.announcements)} price-sensitive announcements")

        announcement_symbols = [
            (ann.ticker, ann.headline, datetime.fromisoformat(ann.timestamp))
            for ann in scan_result.announcements
        ]

        candidates = await self.announcement_gap_scanner.scan_candidates(
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

        opening_ranges = await self.announcement_gap_scanner.sample_opening_ranges(candidates)

        return candidates, opening_ranges


announcement_gap_strategy_service: AnnouncementGapStrategyService | None = None


def get_announcement_gap_strategy_service(
    asx_scanner_config: ScannerConfig,
    min_price: float = 0.20,
    min_gap_pct: float = 0.0,
    lookback_months: int = 6,
) -> AnnouncementGapStrategyService:
    """Get or create announcement gap strategy service singleton.

    Args:
        asx_scanner_config: ASX announcement scanner configuration
        min_price: Minimum stock price threshold
        min_gap_pct: Minimum gap percentage
        lookback_months: Lookback period for high calculation

    Returns:
        AnnouncementGapStrategyService instance
    """
    global announcement_gap_strategy_service
    if announcement_gap_strategy_service is None:
        announcement_gap_strategy_service = AnnouncementGapStrategyService(
            asx_scanner_config,
            min_price=min_price,
            min_gap_pct=min_gap_pct,
            lookback_months=lookback_months,
        )
    return announcement_gap_strategy_service
