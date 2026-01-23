"""Gap scanner API router for FastAPI."""

from datetime import datetime
from typing import TYPE_CHECKING

from fastapi import APIRouter, HTTPException

from app.scanners.gap.models import (
    GapCandidate,
    OpeningRange,
    ScanRequest,
    ScanResponse,
    ScanStatus,
)
from app.scanners.gap.scanner import GapScanner

if TYPE_CHECKING:
    pass

router = APIRouter(prefix="/scanner", tags=["scanner"])
gap_scanner: GapScanner | None = None


def init_scanner() -> None:
    """Initialize the global gap scanner instance."""
    global gap_scanner

    from app.database import get_database_manager

    gap_scanner = GapScanner(get_database_manager())


@router.post("/gap/start")
async def start_gap_scan(request: ScanRequest) -> ScanResponse:
    """Start a gap scan with specified parameters.

    Args:
        request: Scan request with parameters

    Returns:
        Scan response with results
    """
    global gap_scanner

    if gap_scanner is None:
        raise HTTPException(status_code=500, detail="Gap scanner not initialized")

    return await gap_scanner.start_scan(request)


@router.get("/gap/results/{scan_id}")
async def get_scan_results(_scan_id: str) -> list[GapCandidate]:
    """Get results for a completed scan.

    Note: Currently returns last scan results. In production, implement scan ID tracking.

    Args:
        _scan_id: Scan ID

    Returns:
        List of gap candidates
    """
    global gap_scanner

    if gap_scanner is None:
        raise HTTPException(status_code=500, detail="Gap scanner not initialized")

    status = await gap_scanner.get_status()

    if status.last_scan_results == 0:
        raise HTTPException(status_code=404, detail="No scan results available")

    candidates = await gap_scanner.get_candidates_for_date(datetime.now())

    return candidates


@router.get("/gap/candidates/{date}")
async def get_gap_candidates(date: datetime) -> list[GapCandidate]:
    """Get gap candidates for a specific date.

    Args:
        date: Date to query

    Returns:
        List of gap candidates
    """
    global gap_scanner

    if gap_scanner is None:
        raise HTTPException(status_code=500, detail="Gap scanner not initialized")

    return await gap_scanner.get_candidates_for_date(date)


@router.get("/opening-range/{date}")
async def get_opening_ranges(_date: datetime) -> list[OpeningRange]:
    """Get opening ranges for a specific date.

    Args:
        _date: Date to query

    Returns:
        List of opening ranges
    """
    global gap_scanner

    if gap_scanner is None:
        raise HTTPException(status_code=500, detail="Gap scanner not initialized")

    status = await gap_scanner.get_status()

    if status.last_scan_results == 0:
        raise HTTPException(status_code=404, detail="No opening range data available")

    return list(gap_scanner.or_tracker._or_cache.values())


@router.get("/status")
async def get_scanner_status() -> ScanStatus:
    """Get current scanner status.

    Returns:
        Scanner status
    """
    global gap_scanner

    if gap_scanner is None:
        raise HTTPException(status_code=500, detail="Gap scanner not initialized")

    return await gap_scanner.get_status()
