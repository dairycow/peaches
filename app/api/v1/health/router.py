"""Health check endpoint for monitoring."""

from datetime import datetime

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from app.config import config
from app.services.health_service import HealthStatus, health_checker

router = APIRouter(prefix="/health", tags=["health"])


class HealthResponse(BaseModel):
    """Health check response model."""

    status: HealthStatus
    timestamp: datetime
    gateway_connected: bool
    uptime_seconds: float
    version: str


@router.get("", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Health check endpoint.

    Returns:
        HealthResponse with current status
    """
    return HealthResponse(
        status=health_checker.get_status(),
        timestamp=datetime.now(),
        gateway_connected=health_checker.gateway_connected,
        uptime_seconds=health_checker.get_uptime(),
        version="0.1.0",
    )


@router.get("/gateway")
async def check_gateway() -> dict[str, bool | int]:
    """Check gateway connection status.

    Returns:
        Dictionary with gateway status
    """
    return {
        "connected": health_checker.gateway_connected,
        "consecutive_failures": health_checker.consecutive_failures,
        "threshold": config.health.unhealthy_threshold,
    }


@router.get("/ready")
async def readiness_check() -> dict[str, bool | HealthStatus]:
    """Readiness check endpoint.

    Returns:
        Dictionary indicating readiness status

    Raises:
        HTTPException: If not ready
    """
    health_status = health_checker.get_status()

    if health_status == HealthStatus.UNHEALTHY:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Service unhealthy: {health_checker.consecutive_failures} consecutive failures",
        )

    if health_status == HealthStatus.DEGRADED:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Service degraded: gateway not connected",
        )

    return {"ready": True, "status": health_status}


@router.get("/live")
async def liveness_check() -> dict[str, bool | float]:
    """Liveness check endpoint.

    Returns:
        Dictionary indicating liveness status
    """
    return {"alive": True, "uptime_seconds": health_checker.get_uptime()}
