"""API router for announcement gap strategy scanning."""

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.config import config
from app.services.announcement_gap_strategy_service import (
    AnnouncementGapStrategyService,
    get_announcement_gap_strategy_service,
)

router = APIRouter(prefix="/api/v1/announcement-gap", tags=["announcement-gap"])

announcement_gap_service: AnnouncementGapStrategyService | None = None


class AnnouncementGapScanRequest(BaseModel):
    """Request model for announcement gap scan."""

    min_price: float = Field(default=0.20, ge=0.01, description="Minimum stock price")
    min_gap_pct: float = Field(default=0.0, ge=0, description="Minimum gap percentage")
    lookback_months: int = Field(default=6, ge=1, le=24, description="Lookback period for high")


class AnnouncementGapScanResponse(BaseModel):
    """Response model for announcement gap scan."""

    success: bool = Field(..., description="Whether scan succeeded")
    candidates_count: int = Field(..., description="Number of candidates found")
    candidates: list[dict[str, Any]] = Field(default_factory=list, description="Candidate details")
    message: str = Field(..., description="Status message")


class OpeningRangeResponse(BaseModel):
    """Response model for opening range sampling."""

    success: bool = Field(..., description="Whether sampling succeeded")
    opening_ranges: dict[str, float] = Field(
        default_factory=dict, description="Symbol → ORH mapping"
    )
    message: str = Field(..., description="Status message")


@router.post("/scan", response_model=AnnouncementGapScanResponse)
async def scan_announcement_gap(request: AnnouncementGapScanRequest) -> AnnouncementGapScanResponse:
    """Scan for announcement gap breakout candidates.

    Filters stocks by:
    - Made price-sensitive announcement today
    - Positive gap percentage
    - Price > 6-month high
    - Price > minimum threshold
    """
    global announcement_gap_service

    try:
        from app.scanners.asx_price_sensitive import ScannerConfig

        scanner_config = ScannerConfig(
            url=config.scanners.asx.url,
            timeout=config.scanners.asx.timeout,
            exclude_tickers=config.scanners.asx.exclude_tickers,
            min_ticker_length=config.scanners.asx.min_ticker_length,
            max_ticker_length=config.scanners.asx.max_ticker_length,
        )

        announcement_gap_service = get_announcement_gap_strategy_service(
            scanner_config,
            min_price=request.min_price,
            min_gap_pct=request.min_gap_pct,
            lookback_months=request.lookback_months,
        )

        candidates = await announcement_gap_service.run_daily_scan()

        candidate_dicts = [
            {
                "symbol": c.symbol,
                "gap_pct": c.gap_pct,
                "six_month_high": c.six_month_high,
                "current_price": c.current_price,
                "announcement_headline": c.announcement_headline,
                "announcement_time": c.announcement_time.isoformat(),
                "exchange": c.exchange.value,
            }
            for c in candidates
        ]

        return AnnouncementGapScanResponse(
            success=True,
            candidates_count=len(candidates),
            candidates=candidate_dicts,
            message=f"Found {len(candidates)} candidates",
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Scan failed: {str(e)}") from e


@router.post("/sample-opening-ranges", response_model=OpeningRangeResponse)
async def sample_opening_ranges(request: AnnouncementGapScanRequest) -> OpeningRangeResponse:
    """Scan candidates and sample opening ranges.

    Returns candidates along with their 5-minute opening range highs.
    """
    global announcement_gap_service

    try:
        from app.scanners.asx_price_sensitive import ScannerConfig

        scanner_config = ScannerConfig(
            url=config.scanners.asx.url,
            timeout=config.scanners.asx.timeout,
            exclude_tickers=config.scanners.asx.exclude_tickers,
            min_ticker_length=config.scanners.asx.min_ticker_length,
            max_ticker_length=config.scanners.asx.max_ticker_length,
        )

        announcement_gap_service = get_announcement_gap_strategy_service(
            scanner_config,
            min_price=request.min_price,
            min_gap_pct=request.min_gap_pct,
            lookback_months=request.lookback_months,
        )

        candidates, opening_ranges = await announcement_gap_service.scan_and_sample_opening_ranges()

        return OpeningRangeResponse(
            success=True,
            opening_ranges=opening_ranges,
            message=f"Sampled opening ranges for {len(opening_ranges)} candidates",
        )

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Opening range sampling failed: {str(e)}"
        ) from e
