"""IBKR scanner API endpoints."""

import uuid

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from app.config import config
from app.container import get_ibkr_scanner_service
from app.events.bus import get_event_bus
from app.events.events import IBKRScanStartedEvent

router = APIRouter(prefix="/ibkr-scanner", tags=["ibkr-scanner"])


class ScanTriggerResponse(BaseModel):
    """Response for scan trigger."""

    message: str
    correlation_id: str


class ScannerStatusResponse(BaseModel):
    """Response for scanner status."""

    enabled: bool
    scan_schedule: str
    running: bool
    connected: bool
    last_scan_time: str | None


@router.post("/trigger", response_model=ScanTriggerResponse)
async def trigger_ibkr_scan() -> ScanTriggerResponse:
    """Trigger manual IBKR gap scan."""
    if not config.ibkr_scanner.enabled:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="IBKR scanner is disabled in configuration",
        )

    event_bus = get_event_bus()
    correlation_id = str(uuid.uuid4())

    await event_bus.publish(IBKRScanStartedEvent(source="manual", correlation_id=correlation_id))

    return ScanTriggerResponse(
        message="IBKR scan job triggered",
        correlation_id=correlation_id,
    )


@router.get("/status", response_model=ScannerStatusResponse)
async def get_ibkr_scanner_status() -> ScannerStatusResponse:
    """Get IBKR scanner status."""
    scanner_service = get_ibkr_scanner_service()

    health = await scanner_service.health_check()

    return ScannerStatusResponse(
        enabled=config.ibkr_scanner.enabled,
        scan_schedule=config.ibkr_scanner.scan_schedule,
        running=health["running"],
        connected=health["connected"],
        last_scan_time=health.get("last_scan_time"),
    )
