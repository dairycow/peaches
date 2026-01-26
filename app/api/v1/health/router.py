"""Health check endpoint for monitoring."""

from datetime import datetime

from fastapi import APIRouter
from pydantic import BaseModel

from app.container import get_config, get_health_checker
from app.services.health_service import HealthStatus

router = APIRouter(prefix="/health", tags=["health"])
get_health_checker_dep = get_health_checker
get_config_dep = get_config


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
    health_checker = get_health_checker_dep()
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
    health_checker = get_health_checker_dep()
    config = get_config_dep()
    return {
        "connected": health_checker.gateway_connected,
        "consecutive_failures": health_checker.consecutive_failures,
        "threshold": config.health.unhealthy_threshold,
    }


@router.get("/ready")
async def readiness_check() -> dict[str, str]:
    """Readiness probe for Kubernetes.

    Returns:
        Dictionary indicating service is ready
    """
    return {"status": "ready"}


@router.get("/live")
async def liveness_check() -> dict[str, str]:
    """Liveness probe for Kubernetes.

    Returns:
        Dictionary indicating service is alive
    """
    return {"status": "alive"}
