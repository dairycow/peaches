"""Health monitoring service."""

from datetime import datetime
from enum import Enum

from app.config import config


class HealthStatus(str, Enum):
    """Health status enumeration."""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


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
