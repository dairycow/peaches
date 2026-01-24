"""FastAPI endpoints for historical data management."""

from datetime import datetime
from typing import cast

from fastapi import APIRouter, BackgroundTasks, HTTPException, status
from loguru import logger
from pydantic import BaseModel

from app.config import config
from app.external.cooltrader import create_downloader
from app.external.vnpy.database import get_database_manager
from app.scheduler import get_scheduler

router = APIRouter(prefix="/import", tags=["historical-data"])


class JobTriggerResponse(BaseModel):
    """Response model for job trigger endpoints."""

    message: str
    job_id: str


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
    download_schedule: str
    import_schedule: str
    timezone: str


@router.post("/download/trigger", response_model=JobTriggerResponse)
async def trigger_download(background_tasks: BackgroundTasks) -> JobTriggerResponse:
    """Trigger manual CoolTrader download.

    Returns:
        Task status
    """
    if not config.historical_data.import_enabled:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Import is disabled in configuration",
        )

    from app.scheduler import run_download

    background_tasks.add_task(run_download)

    return JobTriggerResponse(
        message="Download job started in background",
        job_id="cooltrader_download",
    )


@router.post("/import/trigger", response_model=JobTriggerResponse)
async def trigger_import(background_tasks: BackgroundTasks) -> JobTriggerResponse:
    """Trigger manual CSV import.

    Returns:
        Task status
    """
    if not config.historical_data.import_enabled:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Import is disabled in configuration",
        )

    from app.scheduler import run_import

    background_tasks.add_task(run_import)

    return JobTriggerResponse(
        message="Import job started in background",
        job_id="csv_import",
    )


@router.post("/schedule/start", response_model=SchedulerStatusResponse)
async def start_scheduler() -> SchedulerStatusResponse:
    """Start scheduled downloads and imports.

    Returns:
        Scheduler status
    """
    if not config.historical_data.import_enabled:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Import is disabled in configuration",
        )

    scheduler = get_scheduler()

    if scheduler.is_running():
        return SchedulerStatusResponse(
            enabled=config.historical_data.import_enabled,
            running=True,
            download_schedule=config.cooltrader.download_schedule,
            import_schedule=config.cooltrader.import_schedule,
            timezone="Australia/Sydney",
        )

    await scheduler.start()

    return SchedulerStatusResponse(
        enabled=config.historical_data.import_enabled,
        running=True,
        download_schedule=config.cooltrader.download_schedule,
        import_schedule=config.cooltrader.import_schedule,
        timezone="Australia/Sydney",
    )


@router.post("/schedule/stop", response_model=SchedulerStatusResponse)
async def stop_scheduler() -> SchedulerStatusResponse:
    """Stop scheduled downloads and imports.

    Returns:
        Scheduler status
    """
    scheduler = get_scheduler()

    if not scheduler.is_running():
        return SchedulerStatusResponse(
            enabled=config.historical_data.import_enabled,
            running=False,
            download_schedule=config.cooltrader.download_schedule,
            import_schedule=config.cooltrader.import_schedule,
            timezone="Australia/Sydney",
        )

    await scheduler.stop()

    return SchedulerStatusResponse(
        enabled=config.historical_data.import_enabled,
        running=False,
        download_schedule=config.cooltrader.download_schedule,
        import_schedule=config.cooltrader.import_schedule,
        timezone="Australia/Sydney",
    )


@router.get("/schedule/status", response_model=SchedulerStatusResponse)
async def schedule_status() -> SchedulerStatusResponse:
    """Get scheduler status.

    Returns:
        Scheduler status dictionary
    """
    scheduler = get_scheduler()

    return SchedulerStatusResponse(
        enabled=config.historical_data.import_enabled,
        running=scheduler.is_running(),
        download_schedule=config.cooltrader.download_schedule,
        import_schedule=config.cooltrader.import_schedule,
        timezone="Australia/Sydney",
    )


@router.get("/database/stats", response_model=DatabaseStatsResponse)
async def get_database_stats_endpoint() -> DatabaseStatsResponse:
    """Get database statistics.

    Returns:
        Database statistics
    """
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
    """Get database overview.

    Returns:
        Database overview with symbol details
    """
    db_manager = get_database_manager()
    overview = db_manager.get_database_overview()

    return DatabaseOverviewResponse(
        total_symbols=cast(int, overview["total_symbols"]),
        symbols=cast(list[dict[str, str | int | None]], overview["symbols"]),
    )


class DownloadDateRequest(BaseModel):
    """Request model for manual date download."""

    date: str


@router.post("/download/date", response_model=JobTriggerResponse)
async def download_specific_date(
    request: DownloadDateRequest, background_tasks: BackgroundTasks
) -> JobTriggerResponse:
    """Manually download CSV for specific date.

    Args:
        request: Date in YYYY-MM-DD format
        background_tasks: FastAPI background tasks

    Returns:
        Download task status

    Raises:
        HTTPException: If date format is invalid or download fails
    """
    try:
        parsed_date = datetime.strptime(request.date, "%Y-%m-%d")
        target_date = parsed_date.date()
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

    async def download_task() -> None:
        try:
            downloader = create_downloader()
            filepath = await downloader.download_csv(target_date)
            await downloader.close()
            logger.info(f"Manual download completed: {filepath}")
        except Exception as e:
            logger.error(f"Manual download failed: {e}")

    background_tasks.add_task(download_task)

    return JobTriggerResponse(
        message=f"Download job started for {request.date} in background",
        job_id=f"cooltrader_download_{request.date}",
    )
