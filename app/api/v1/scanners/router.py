"""API v1 scanner endpoints."""

import uuid

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from app.config import config
from app.events.bus import get_event_bus

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
