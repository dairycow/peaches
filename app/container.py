"""FastAPI dependency helpers."""

from typing import TYPE_CHECKING

from app.config import config
from app.external.vnpy.database import DatabaseManager
from app.external.vnpy.database import get_database_manager as vnpy_get_db

if TYPE_CHECKING:
    from app.services.ibkr_scanner_service import IBKRScannerService

_ibkr_scanner_service: "IBKRScannerService | None" = None


def get_config():
    """Get config for FastAPI dependency injection.

    Returns:
        Config singleton (module-level)
    """
    return config


def get_database_manager() -> DatabaseManager:
    """Get database manager for FastAPI dependency injection.

    Returns:
        DatabaseManager singleton (from vn.py)
    """
    return vnpy_get_db()


def get_gateway_service():
    """Get gateway service for FastAPI dependency injection.

    Returns:
        GatewayService singleton (module-level)
    """
    from app.services.gateway_service import gateway_service

    return gateway_service


def get_health_checker():
    """Get health checker for FastAPI dependency injection.

    Returns:
        HealthChecker singleton (module-level)
    """
    from app.services.health_service import health_checker

    return health_checker


def get_ibkr_scanner_service() -> "IBKRScannerService":
    """Get IBKR scanner service for FastAPI dependency injection.

    Returns:
        IBKRScannerService singleton (creates if not exists)
    """
    global _ibkr_scanner_service
    if _ibkr_scanner_service is None:
        from app.events.bus import get_event_bus
        from app.services.ibkr_scanner_service import IBKRScannerService

        event_bus = get_event_bus()
        _ibkr_scanner_service = IBKRScannerService(config.ibkr_scanner, event_bus)
    return _ibkr_scanner_service
