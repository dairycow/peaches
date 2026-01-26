"""FastAPI dependency helpers."""

from app.config import config
from app.external.vnpy.database import DatabaseManager
from app.external.vnpy.database import get_database_manager as vnpy_get_db


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
