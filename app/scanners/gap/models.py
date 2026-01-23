"""Pydantic models for gap scanner."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class GapCandidate(BaseModel):
    """Gap candidate detected by scanner."""

    symbol: str = Field(..., description="Stock symbol")
    gap_percent: float = Field(..., ge=0, description="Gap percentage")
    gap_direction: Literal["up", "down"] = Field(..., description="Gap direction")
    previous_close: float = Field(..., description="Previous day close price")
    open_price: float = Field(..., description="Today's open price")
    volume: int = Field(..., description="Today's volume")
    price: float = Field(..., description="Current price")
    timestamp: datetime = Field(default_factory=datetime.now, description="Scan timestamp")
    conid: int = Field(..., description="IB contract ID")


class OpeningRange(BaseModel):
    """Opening range for a stock."""

    symbol: str = Field(..., description="Stock symbol")
    orh: float = Field(..., description="Opening range high")
    orl: float = Field(..., description="Opening range low")
    price: float = Field(..., description="Current price")
    sample_time: datetime = Field(..., description="Sample time")


class ScanRequest(BaseModel):
    """Request parameters for gap scan."""

    gap_threshold: float = Field(default=3.0, ge=0, le=50, description="Minimum gap percentage")
    min_price: float = Field(default=1.0, ge=0.01, description="Minimum stock price")
    min_volume: int = Field(default=100000, gt=0, description="Minimum daily volume")
    max_results: int = Field(default=50, ge=1, le=50, description="Maximum results to return")
    scan_direction: Literal["up", "down", "both"] = Field(
        default="both",
        description="Gap direction to scan for",
    )


class ScanStatus(BaseModel):
    """Status of gap scanner."""

    running: bool = Field(..., description="Whether scanner is running")
    last_scan_time: datetime | None = Field(None, description="Last scan timestamp")
    last_scan_results: int = Field(0, description="Number of results from last scan")
    active_scans: int = Field(0, description="Number of active IB scanner requests")


class ScanResponse(BaseModel):
    """Response to scan request."""

    success: bool = Field(..., description="Whether scan was successful")
    scan_id: str = Field(..., description="Unique scan identifier")
    candidates_count: int = Field(..., description="Number of candidates found")
    estimated_completion: datetime | None = Field(None, description="Estimated completion time")
    message: str = Field(..., description="Status message")
