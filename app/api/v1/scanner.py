"""Scanner API endpoints."""

import uuid
from datetime import datetime

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from app.config import config
from app.events.bus import get_event_bus
from app.scanners.gap.models import (
    GapCandidate,
    OpeningRange,
    ScanRequest,
    ScanResponse,
    ScanStatus,
)
from app.scanners.gap.scanner import GapScanner

router = APIRouter(prefix="/scanner", tags=["scanner"])
gap_scanner: GapScanner | None = None


class ScanTriggerResponse(BaseModel):
    """Response model for scan trigger."""

    message: str


class ScannerStatusResponse(BaseModel):
    """Response model for scanner status."""

    enabled: bool
    scan_schedule: str
    timezone: str


def init_scanner() -> None:
    """Initialize the global gap scanner instance."""
    global gap_scanner

    from app.external.database import get_database_manager

    gap_scanner = GapScanner(get_database_manager())


@router.post("/gap/start")
async def start_gap_scan(request: ScanRequest) -> ScanResponse:
    """Start a gap scan with specified parameters."""
    global gap_scanner

    if gap_scanner is None:
        raise HTTPException(status_code=500, detail="Gap scanner not initialized")

    return await gap_scanner.start_scan(request)


@router.get("/gap/results/{scan_id}")
async def get_scan_results(_scan_id: str) -> list[GapCandidate]:
    """Get results for a completed scan."""
    global gap_scanner

    if gap_scanner is None:
        raise HTTPException(status_code=500, detail="Gap scanner not initialized")

    scan_status = await gap_scanner.get_status()

    if scan_status.last_scan_results == 0:
        raise HTTPException(status_code=404, detail="No scan results available")

    return await gap_scanner.get_candidates_for_date(datetime.now())


@router.get("/gap/candidates/{date}")
async def get_gap_candidates(date: datetime) -> list[GapCandidate]:
    """Get gap candidates for a specific date."""
    global gap_scanner

    if gap_scanner is None:
        raise HTTPException(status_code=500, detail="Gap scanner not initialized")

    return await gap_scanner.get_candidates_for_date(date)


@router.get("/opening-range/{date}")
async def get_opening_ranges(_date: datetime) -> list[OpeningRange]:
    """Get opening ranges for a specific date."""
    global gap_scanner

    if gap_scanner is None:
        raise HTTPException(status_code=500, detail="Gap scanner not initialized")

    scan_status = await gap_scanner.get_status()

    if scan_status.last_scan_results == 0:
        raise HTTPException(status_code=404, detail="No opening range data available")

    return list(gap_scanner._or_cache.values())


@router.get("/gap/status")
async def get_gap_scanner_status() -> ScanStatus:
    """Get current gap scanner status."""
    global gap_scanner

    if gap_scanner is None:
        raise HTTPException(status_code=500, detail="Gap scanner not initialized")

    return await gap_scanner.get_status()


@router.post("/trigger", response_model=ScanTriggerResponse)
async def trigger_scan() -> ScanTriggerResponse:
    """Trigger manual announcement scan."""
    if not config.scanners.enabled:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Scanners are disabled in configuration",
        )

    from app.events.events import ScanStartedEvent

    event_bus = get_event_bus()
    correlation_id = str(uuid.uuid4())

    await event_bus.publish(ScanStartedEvent(source="manual", correlation_id=correlation_id))

    return ScanTriggerResponse(message="Scan job triggered")


@router.get("/status", response_model=ScannerStatusResponse)
async def get_scanner_status() -> ScannerStatusResponse:
    """Get scanner status."""
    return ScannerStatusResponse(
        enabled=config.scanners.enabled,
        scan_schedule=config.scanners.asx.scan_schedule,
        timezone="Australia/Sydney",
    )
