"""FastAPI dependency helpers."""

from app.config import config
from app.external.database import DatabaseManager, get_database_manager


def get_config():
    """Get config for FastAPI dependency injection.

    Returns:
        Config singleton (module-level)
    """
    return config


def get_db() -> DatabaseManager:
    """Get database manager for FastAPI dependency injection.

    Returns:
        DatabaseManager singleton
    """
    return get_database_manager()


def get_health_checker():
    """Get health checker for FastAPI dependency injection.

    Returns:
        HealthChecker singleton (module-level)
    """
    from app.services.health_service import health_checker

    return health_checker
