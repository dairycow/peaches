"""FastAPI endpoints for historical data management."""

import uuid
from datetime import datetime
from typing import cast

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from app.config import config
from app.events.bus import get_event_bus
from app.external.vnpy.database import get_database_manager

router = APIRouter(prefix="/import", tags=["historical-data"])


class JobTriggerResponse(BaseModel):
    """Response model for job trigger endpoints."""

    message: str


class DatabaseStatsResponse(BaseModel):
    """Response model for database stats."""

    db_path: str
    db_size_bytes: int
    db_size_mb: float
    total_symbols: int
    total_bars: int


class DatabaseOverviewResponse(BaseModel):
    """Response model for database overview."""

    total_symbols: int
    symbols: list[dict[str, str | int | None]]


class SchedulerStatusResponse(BaseModel):
    """Response model for scheduler status."""

    enabled: bool
    running: bool
    scan_schedule: str
    download_schedule: str
    import_schedule: str
    timezone: str


@router.post("/download/trigger", response_model=JobTriggerResponse)
async def trigger_download() -> JobTriggerResponse:
    """Trigger manual CoolTrader download."""
    if not config.historical_data.import_enabled:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Import is disabled in configuration",
        )

    from app.events.events import DownloadStartedEvent

    event_bus = get_event_bus()
    correlation_id = str(uuid.uuid4())

    await event_bus.publish(
        DownloadStartedEvent(source="manual", correlation_id=correlation_id, target_date=None)
    )

    return JobTriggerResponse(message="Download job triggered")


class DownloadDateRequest(BaseModel):
    """Request model for manual date download."""

    date: str


@router.post("/download/date", response_model=JobTriggerResponse)
async def download_specific_date(request: DownloadDateRequest) -> JobTriggerResponse:
    """Manually download CSV for specific date."""
    try:
        datetime.strptime(request.date, "%Y-%m-%d")
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid date format: {e}",
        ) from None

    if not config.historical_data.import_enabled:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Import is disabled in configuration",
        )

    from app.events.events import DownloadStartedEvent

    event_bus = get_event_bus()
    correlation_id = str(uuid.uuid4())

    await event_bus.publish(
        DownloadStartedEvent(
            source="manual",
            correlation_id=correlation_id,
            target_date=request.date,
        )
    )

    return JobTriggerResponse(message=f"Download job triggered for {request.date}")


@router.post("/import/trigger", response_model=JobTriggerResponse)
async def trigger_import() -> JobTriggerResponse:
    """Trigger manual CSV import."""
    if not config.historical_data.import_enabled:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Import is disabled in configuration",
        )

    from app.events.events import ImportStartedEvent

    event_bus = get_event_bus()
    correlation_id = str(uuid.uuid4())

    await event_bus.publish(ImportStartedEvent(source="manual", correlation_id=correlation_id))

    return JobTriggerResponse(message="Import job triggered")


@router.post("/schedule/start", response_model=SchedulerStatusResponse)
async def start_scheduler() -> SchedulerStatusResponse:
    """Start scheduled downloads and imports."""
    if not config.historical_data.import_enabled:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Import is disabled in configuration",
        )

    from app.scheduler import get_scheduler_service

    event_bus = get_event_bus()
    scheduler = await get_scheduler_service(event_bus)

    if scheduler.is_running():
        return SchedulerStatusResponse(
            enabled=config.historical_data.import_enabled,
            running=True,
            scan_schedule=config.scanners.asx.scan_schedule,
            download_schedule=config.cooltrader.download_schedule,
            import_schedule=config.cooltrader.import_schedule,
            timezone="Australia/Sydney",
        )

    await scheduler.start()

    return SchedulerStatusResponse(
        enabled=config.historical_data.import_enabled,
        running=True,
        scan_schedule=config.scanners.asx.scan_schedule,
        download_schedule=config.cooltrader.download_schedule,
        import_schedule=config.cooltrader.import_schedule,
        timezone="Australia/Sydney",
    )


@router.post("/schedule/stop", response_model=SchedulerStatusResponse)
async def stop_scheduler() -> SchedulerStatusResponse:
    """Stop scheduled downloads and imports."""
    from app.scheduler import get_scheduler_service

    event_bus = get_event_bus()
    scheduler = await get_scheduler_service(event_bus)

    if not scheduler.is_running():
        return SchedulerStatusResponse(
            enabled=config.historical_data.import_enabled,
            running=False,
            scan_schedule=config.scanners.asx.scan_schedule,
            download_schedule=config.cooltrader.download_schedule,
            import_schedule=config.cooltrader.import_schedule,
            timezone="Australia/Sydney",
        )

    await scheduler.stop()

    return SchedulerStatusResponse(
        enabled=config.historical_data.import_enabled,
        running=False,
        scan_schedule=config.scanners.asx.scan_schedule,
        download_schedule=config.cooltrader.download_schedule,
        import_schedule=config.cooltrader.import_schedule,
        timezone="Australia/Sydney",
    )


@router.get("/schedule/status", response_model=SchedulerStatusResponse)
async def schedule_status() -> SchedulerStatusResponse:
    """Get scheduler status."""
    from app.scheduler import get_scheduler_service

    event_bus = get_event_bus()
    scheduler = await get_scheduler_service(event_bus)

    return SchedulerStatusResponse(
        enabled=config.historical_data.import_enabled,
        running=scheduler.is_running(),
        scan_schedule=config.scanners.asx.scan_schedule,
        download_schedule=config.cooltrader.download_schedule,
        import_schedule=config.cooltrader.import_schedule,
        timezone="Australia/Sydney",
    )


@router.get("/database/stats", response_model=DatabaseStatsResponse)
async def get_database_stats_endpoint() -> DatabaseStatsResponse:
    """Get database statistics."""
    db_manager = get_database_manager()
    stats = db_manager.get_database_stats()

    return DatabaseStatsResponse(
        db_path=cast(str, stats["db_path"]),
        db_size_bytes=cast(int, stats["db_size_bytes"]),
        db_size_mb=cast(float, stats["db_size_mb"]),
        total_symbols=cast(int, stats["total_symbols"]),
        total_bars=cast(int, stats["total_bars"]),
    )


@router.get("/database/overview", response_model=DatabaseOverviewResponse)
async def get_database_overview_endpoint() -> DatabaseOverviewResponse:
    """Get database overview."""
    db_manager = get_database_manager()
    overview = db_manager.get_database_overview()

    return DatabaseOverviewResponse(
        total_symbols=cast(int, overview["total_symbols"]),
        symbols=cast(list[dict[str, str | int | None]], overview["symbols"]),
    )
