"""API v1 scanner endpoints."""

from fastapi import APIRouter, BackgroundTasks, HTTPException, status
from pydantic import BaseModel

from app.config import config

router = APIRouter(prefix="/scanners", tags=["scanners"])


class ScanTriggerResponse(BaseModel):
    """Response model for scan trigger."""

    message: str


class ScannerStatusResponse(BaseModel):
    """Response model for scanner status."""

    enabled: bool
    scan_schedule: str
    timezone: str


@router.post("/trigger", response_model=ScanTriggerResponse)
async def trigger_scan(background_tasks: BackgroundTasks) -> ScanTriggerResponse:
    """Trigger manual announcement scan.

    Returns:
        Scan trigger response
    """
    if not config.scanners.enabled:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Scanners are disabled in configuration",
        )

    from app.scheduler import run_scan

    background_tasks.add_task(run_scan)

    return ScanTriggerResponse(
        message="Scan job started in background",
    )


@router.get("/status", response_model=ScannerStatusResponse)
async def get_scanner_status() -> ScannerStatusResponse:
    """Get scanner status.

    Returns:
        Scanner status
    """
    return ScannerStatusResponse(
        enabled=config.scanners.enabled,
        scan_schedule=config.scanners.asx.scan_schedule,
        timezone="Australia/Sydney",
    )
