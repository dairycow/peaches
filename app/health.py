"""Health check endpoint for monitoring."""

from datetime import datetime
from enum import Enum

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from app.config import config

router = APIRouter(prefix="/health", tags=["health"])


class HealthStatus(str, Enum):
    """Health status enumeration."""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


class HealthResponse(BaseModel):
    """Health check response model."""

    status: HealthStatus
    timestamp: datetime
    gateway_connected: bool
    uptime_seconds: float
    version: str


class HealthChecker:
    """Health check manager."""

    def __init__(self) -> None:
        """Initialize health checker."""
        self.start_time = datetime.now()
        self.gateway_connected = False
        self.consecutive_failures = 0

    def set_gateway_status(self, connected: bool) -> None:
        """Update gateway connection status.

        Args:
            connected: Whether gateway is connected
        """
        if connected:
            self.consecutive_failures = 0
        else:
            self.consecutive_failures += 1
        self.gateway_connected = connected

    def get_status(self) -> HealthStatus:
        """Get current health status.

        Returns:
            HealthStatus enum value
        """
        if self.consecutive_failures >= config.health.unhealthy_threshold:
            return HealthStatus.UNHEALTHY
        if not self.gateway_connected:
            return HealthStatus.DEGRADED
        return HealthStatus.HEALTHY

    def get_uptime(self) -> float:
        """Get application uptime in seconds.

        Returns:
            Uptime in seconds
        """
        return (datetime.now() - self.start_time).total_seconds()


health_checker = HealthChecker()


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
async def check_gateway() -> dict:
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
async def readiness_check() -> dict:
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
async def liveness_check() -> dict:
    """Liveness check endpoint.

    Returns:
        Dictionary indicating liveness status
    """
    return {"alive": True, "uptime_seconds": health_checker.get_uptime()}
