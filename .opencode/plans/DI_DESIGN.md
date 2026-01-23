# Dependency Injection Design Document

## 1. Current State Audit

### 1.1 Global Singletons Mapping

| Singleton | Location | Type | Initialization | Dependencies |
|-----------|----------|------|----------------|--------------|
| `config` | `app/config.py:308` | Module-level | At module import | None |
| `gateway_manager` | `app/gateway.py:269` | Module-level | At module import | `config` |
| `health_checker` | `app/services/health_service.py:59` | Module-level | At module import | `config` |
| `gateway_service` | `app/services/gateway_service.py:61` | Module-level | At module import | `gateway_manager`, `health_checker`, `config` |
| `strategy_service` | `app/services/strategy_service.py:73` | Module-level | At module import | `gateway_manager` (lazy) |
| `_database_manager` | `app/database.py:208` | Module-level | Lazy via `get_database_manager()` | `config` |
| `scheduler` | `app/scheduler/import_scheduler.py:172` | Module-level | Lazy via `get_scheduler()` | `config` |
| `scanner_scheduler` | `app/scheduler/scanner_scheduler.py:144` | Module-level | Lazy via `get_scanner_scheduler()` | `config` |
| `gap_scanner` | `app/api/v1/scanner.py:15` | Module-level | Via `init_scanner()` | `get_database_manager()` |
| `notification_service` | `app/services/notification_service.py:58` | Module-level | Lazy via `get_notification_service()` | None |
| `strategy_trigger_service` | `app/services/strategy_trigger_service.py:55` | Module-level | Lazy via `get_strategy_trigger_service()` | None |
| `scanner_service` | `app/services/scanner_service.py:102` | Module-level | Lazy via `get_scanner_service()` | `scanner`, `notification_service`, `strategy_trigger_service` |
| `announcement_gap_strategy_service` | `app/services/announcement_gap_strategy_service.py:95` | Module-level | Lazy via `get_announcement_gap_strategy_service()` | `ASXPriceSensitiveScanner`, `AnnouncementGapScanner` |
| `announcement_gap_service` | `app/api/v1/announcement_gap/router.py:16` | Module-level | Lazy via endpoint handler | `get_announcement_gap_strategy_service()` |

### 1.2 Import/Usage Analysis

#### Direct Global Imports (Tight Coupling)

**`app/config.py`** (No dependencies)
- Imported by: 35+ modules across codebase

**`app/database.py`**
- Imported by: `app/scanner/scanner.py`, `app/scanner/announcement_gap_scanner.py`, `app/analysis/data_loader.py`, `app/importer.py`, `app/api/v1/scanner.py`, `app/api/v1/historical_data/router.py`
- Pattern: `from app.database import get_database_manager`
- Usage: Creates new DatabaseManager instances or calls `get_database_manager()`

**`app/gateway.py`**
- Imported by: `app/services/gateway_service.py`, `app/services/strategy_service.py`, `app/main.py`
- Pattern: `from app.gateway import gateway_manager`
- Usage: Accesses `gateway_manager` singleton directly

**`app/services/health_service.py`**
- Imported by: `app/services/gateway_service.py`, `app/api/v1/health/router.py`, `app/main.py`
- Pattern: `from app.services.health_service import health_checker`
- Usage: Accesses `health_checker` singleton directly

**`app/services/gateway_service.py`**
- Imported by: `app/main.py`, `app/api/v1/scanner.py` (via import)
- Pattern: `from app.services.gateway_service import gateway_service`
- Usage: Accesses `gateway_service` singleton directly

**`app/services/strategy_service.py`**
- Imported by: `app/main.py`
- Pattern: `from app.services.strategy_service import strategy_service`
- Usage: Accesses `strategy_service` singleton directly

### 1.3 Startup Initialization Order (main.py:26-59)

```
1. vnpy SETTINGS configuration
2. Setup logging (uses config)
3. Initialize scheduler (get_scheduler())
4. Initialize scanner_scheduler (get_scanner_scheduler())
5. Start gateway_service (starts gateway_manager)
6. Start strategy_service (depends on gateway_manager connection)
7. Initialize scanner (init_scanner())
8. Start scheduler if import_enabled
9. Start scanner_scheduler if scanners.enabled
10. Start health checks
```

### 1.4 Circular Dependency Risks

| Risk Area | Components | Risk Level | Details |
|-----------|-----------|------------|---------|
| Gateway Services | `gateway_service` ↔ `health_checker` ↔ `gateway_manager` | **MEDIUM** | `gateway_service` imports `health_checker` which uses `config`, `health_checker` is updated by `gateway_service` |
| Strategy Service | `strategy_service` ↔ `gateway_manager` ↔ `gateway_service` | **LOW** | `strategy_service.start()` lazy imports `gateway_manager`, which is managed by `gateway_service` |
| Scanner Services | `scanner_service` ↔ `notification_service` ↔ `strategy_trigger_service` ↔ `strategies` | **MEDIUM** | All created dynamically in scheduler, but `strategy_trigger_service` imports `strategies.get_strategy()` which may import more services |

## 2. Dependency Graph

### 2.1 Current Architecture (Text-Based)

```
┌─────────────────────────────────────────────────────────────────┐
│                         Config (Singleton)                        │
│                    app/config.py:308                            │
└───────────────────────────┬─────────────────────────────────────┘
                            │
        ┌───────────────────┼───────────────────┐
        │                   │                   │
        ▼                   ▼                   ▼
┌───────────────┐   ┌──────────────────┐   ┌──────────────────┐
│ HealthChecker │   │  DatabaseManager │   │  GatewayManager  │
│  (Singleton)  │   │  (Lazy Singleton)│   │   (Singleton)    │
└───────┬───────┘   └────────┬─────────┘   └────────┬─────────┘
        │                    │                      │
        │                    │                      │
        ▼                    ▼                      ▼
┌───────────────┐   ┌──────────────────┐   ┌──────────────────┐
│GatewayService │   │   CSVImporter    │   │  GapScanner      │
│  (Singleton)  │   │   (Factory)      │   │  (Singleton*)     │
└───────┬───────┘   └────────┬─────────┘   └────────┬─────────┘
        │                    │                      │
        │                    │                      │
        ▼                    ▼                      ▼
┌───────────────┐   ┌──────────────────┐   ┌──────────────────┐
│StrategyService│   │   ImportScheduler│   │ScannerScheduler  │
│  (Singleton)  │   │  (Lazy Singleton) │   │(Lazy Singleton)  │
└───────────────┘   └──────────────────┘   └──────────────────┘
                                                      │
                                                      ▼
                                           ┌──────────────────┐
                                           │ ScannerService   │
                                           │(Dynamic in run_scan)│
                                           └────────┬─────────┘
                                                    │
                    ┌───────────────────────────────┼───────────────────────────────┐
                    │                               │                               │
                    ▼                               ▼                               ▼
           ┌─────────────────┐           ┌──────────────────┐            ┌──────────────────┐
           │NotificationSrv  │           │StrategyTriggerSrv│            │AnnGapStrategySrv│
           │ (Lazy Singleton)│           │ (Lazy Singleton) │            │ (Lazy Singleton) │
           └─────────────────┘           └────────┬─────────┘            └────────┬─────────┘
                                                │                               │
                                                ▼                               │
                                       ┌──────────────────┐                    │
                                       │   Strategies     │                    │
                                       │ (Dynamic import) │                    │
                                       └──────────────────┘                    │
                                                                              │
                                                                              ▼
                                                                   ┌──────────────────┐
                                                                   │ ASXScanner       │
                                                                   │ (Factory)        │
                                                                   └──────────────────┘

*Note: Tight coupling indicated by direct module-level imports. Singleton* = module-level but initialized later.
```

### 2.2 Tight Coupling Points

| Coupling | From → To | Type | Impact |
|---------|-----------|------|--------|
| `config` | Everywhere | Module import | Hard to test with different configs |
| `gateway_manager` | `gateway_service`, `strategy_service` | Direct singleton | Cannot mock gateway connection |
| `health_checker` | `gateway_service` | Direct singleton | Health checks coupled to service |
| `get_database_manager()` | 6+ modules | Factory function | Cannot inject test database |
| `create_importer()` | `importer.py`, scheduler | Factory function | Creates new instance each call |
| `create_downloader()` | scheduler | Factory function | Creates new instance each call |

## 3. DI Solution Research

### 3.1 Evaluation Matrix

| Solution | Simplicity | Testability | Learning Curve | FastAPI Integration | Async Support | Recommended |
|----------|-----------|-------------|----------------|---------------------|---------------|-------------|
| **FastAPI Depends()** | ★★★★★ | ★★★★☆ | ★★★★★ | Native | ★★★★★ | **YES** |
| **dependency-injector** | ★★★☆☆ | ★★★★★ | ★★★☆☆ | Possible | ★★★☆☆ | NO |
| **inversify (Python port)** | ★★☆☆☆ | ★★★★★ | ★★☆☆☆ | Difficult | ★★☆☆☆ | NO |
| **Custom DI Container** | ★★★☆☆ | ★★★★☆ | ★★★★☆ | Custom integration | ★★★★★ | **YES** |
| **Python's Simple DI** (no lib) | ★★★★★ | ★★★☆☆ | ★★★★★ | Manual | ★★★★★ | NO |

### 3.2 Recommended Solution: Hybrid Approach

**Primary**: FastAPI's native `Depends()` for API routes
**Secondary**: Custom lightweight DI container for non-FastAPI components (services, schedulers)

#### Rationale

1. **FastAPI Depends()**
   - Native to FastAPI, no extra dependencies
   - Automatic request-scoped lifecycle
   - Built-in async support
   - Easy to override with `app.dependency_overrides` for testing
   - Simple to understand for FastAPI developers

2. **Custom DI Container**
   - Lightweight (minimal code, no external deps)
   - Supports singleton, transient, factory lifetimes
   - Explicit registration for better visibility
   - Compatible with async context managers
   - Can work with vn.py blocking calls via `run_in_executor`

### 3.3 Tradeoffs

| Aspect | FastAPI Depends() | Custom Container |
|--------|-------------------|------------------|
| **Pros** | Native, zero-dep, test-friendly | Flexible lifetimes, explicit, works outside FastAPI |
| **Cons** | Request-scoped only, hard for singletons | More boilerplate, custom code to maintain |
| **Best For** | API routes, request handlers | Services, schedulers, CLI tools |

## 4. Design Requirements

### 4.1 Lifetime Support

```python
# Singleton - one instance for entire application
@singleton
class DatabaseManager:
    pass

# Transient - new instance each request
@transient
class CSVImporter:
    pass

# Factory - new instance each call with parameters
@factory
def create_scanner(symbol: str) -> Scanner:
    return Scanner(symbol)
```

### 4.2 FastAPI Integration

```python
# API route using Depends()
@router.get("/health")
async def health_check(
    db: DatabaseManager = Depends(get_database_manager),
    gateway: GatewayManager = Depends(get_gateway_manager),
) -> HealthResponse:
    return HealthResponse(...)
```

### 4.3 Test Override Support

```python
# In tests
app.dependency_overrides[get_database_manager] = lambda: MockDatabaseManager()

# For custom container
container.override(DatabaseManager, MockDatabaseManager)
```

### 4.4 Eliminate Module-Level Globals

**Before**:
```python
# app/services/gateway_service.py
gateway_service = GatewayService()
```

**After**:
```python
# app/container.py
container.singleton(GatewayService, GatewayService)

# app/api/v1/health/router.py
@router.get("/health")
async def health_check(
    gateway: GatewayService = Depends(get_gateway_service),
) -> HealthResponse:
    ...
```

### 4.5 Preserve Existing Behavior

- Gateway startup/shutdown sequence maintained
- Database connection pooling unchanged
- Scheduler job registration preserved
- Health check loop unchanged
- vn.py blocking calls still use `run_in_executor`

## 5. Concrete Implementation

### 5.1 Container Definition

**File: `app/container.py`**

```python
"""Lightweight dependency injection container."""

from collections.abc import Callable
from contextlib import asynccontextmanager
from typing import Any, TypeVar

from loguru import logger

T = TypeVar("T")


class Container:
    """Simple DI container supporting singleton, transient, and factory lifetimes."""

    def __init__(self) -> None:
        self._singletons: dict[type, Any] = {}
        self._transients: dict[type, Callable[..., Any]] = {}
        self._factories: dict[type, Callable[..., Any]] = {}
        self._overrides: dict[type, Callable[..., Any]] = {}

    def singleton(self, cls: type[T], instance: T | None = None) -> None:
        """Register a singleton instance or factory.

        Args:
            cls: Class type for singleton
            instance: Pre-created instance (optional)
        """
        if instance is not None:
            self._singletons[cls] = instance
        else:
            self._factories[cls] = lambda: cls()

    def transient(self, cls: type[T], factory: Callable[..., T]) -> None:
        """Register a transient factory - new instance each call.

        Args:
            cls: Class type for transient
            factory: Factory function to create instances
        """
        self._transients[cls] = factory

    def factory(self, cls: type[T], factory: Callable[..., T]) -> None:
        """Register a factory function with parameters.

        Args:
            cls: Class type for factory
            factory: Factory function accepting parameters
        """
        self._factories[cls] = factory

    def get(self, cls: type[T]) -> T:
        """Resolve a dependency.

        Args:
            cls: Class type to resolve

        Returns:
            Instance of requested class

        Raises:
            KeyError: If class not registered
        """
        if cls in self._overrides:
            return self._overrides[cls]()

        if cls in self._singletons:
            return self._singletons[cls]

        if cls in self._factories:
            factory = self._factories[cls]
            if cls in self._transients:
                return factory()
            else:
                instance = factory()
                self._singletons[cls] = instance
                return instance

        raise KeyError(f"Type {cls} not registered in container")

    def override(self, cls: type[T], factory: Callable[..., T]) -> None:
        """Override a registration for testing.

        Args:
            cls: Class type to override
            factory: Replacement factory
        """
        self._overrides[cls] = factory

    def reset_overrides(self) -> None:
        """Clear all test overrides."""
        self._overrides.clear()

    @asynccontextmanager
    async def lifespan(self) -> Any:
        """Context manager for container lifespan.

        Yields:
            Container instance
        """
        logger.debug("Container lifespan start")
        try:
            yield self
        finally:
            await self.shutdown()
            logger.debug("Container lifespan end")

    async def shutdown(self) -> None:
        """Cleanup container resources."""
        import asyncio

        for instance in self._singletons.values():
            if hasattr(instance, "close"):
                try:
                    await instance.close()
                except Exception as e:
                    logger.error(f"Error closing {instance}: {e}")
            elif hasattr(instance, "stop"):
                try:
                    if asyncio.iscoroutinefunction(instance.stop):
                        await instance.stop()
                    else:
                        instance.stop()
                except Exception as e:
                    logger.error(f"Error stopping {instance}: {e}"


# Global container instance
_container: Container | None = None


def get_container() -> Container:
    """Get or create global container.

    Returns:
        Container instance
    """
    global _container
    if _container is None:
        _container = Container()
        _initialize_container(_container)
    return _container


def _initialize_container(container: Container) -> None:
    """Initialize container with all application dependencies."""
    from app.config import load_config, Config
    
    # Load and validate config explicitly (CRITICAL - see Section 8)
    config = load_config()
    container.singleton(Config, config)
    
    from app.database import DatabaseManager
    from app.gateway import GatewayManager
    from app.services.gateway_service import GatewayService
    from app.services.health_service import HealthChecker
    from app.services.strategy_service import StrategyService
 
    container.singleton(HealthChecker, HealthChecker())
    container.singleton(GatewayManager, GatewayManager())
    container.singleton(GatewayService, GatewayService())
    container.singleton(StrategyService, StrategyService())
    container.singleton(DatabaseManager, DatabaseManager())


def reset_container() -> None:
    """Reset global container (mainly for testing)."""
    global _container
    if _container is not None:
        _container = None
```

### 5.2 FastAPI Integration Helpers

**File: `app/container.py`** (continued)

```python
from fastapi import Depends

def get_config() -> Config:
    """Get config instance for FastAPI dependency injection.

    Returns:
        Config singleton
    """
    from app.config import config
    return config


def get_database_manager() -> DatabaseManager:
    """Get database manager for FastAPI dependency injection.

    Returns:
        DatabaseManager singleton
    """
    return get_container().get(DatabaseManager)


def get_gateway_manager() -> GatewayManager:
    """Get gateway manager for FastAPI dependency injection.

    Returns:
        GatewayManager singleton
    """
    return get_container().get(GatewayManager)


def get_gateway_service() -> GatewayService:
    """Get gateway service for FastAPI dependency injection.

    Returns:
        GatewayService singleton
    """
    return get_container().get(GatewayService)


def get_health_checker() -> HealthChecker:
    """Get health checker for FastAPI dependency injection.

    Returns:
        HealthChecker singleton
    """
    return get_container().get(HealthChecker)
```

### 5.3 Example API Route with DI

**File: `app/api/v1/health/router.py`** (refactored)

```python
"""Health check endpoint for monitoring."""

from datetime import datetime

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from app.container import get_health_checker, get_config
from app.services.health_service import HealthStatus

router = APIRouter(prefix="/health", tags=["health"])


class HealthResponse(BaseModel):
    """Health check response model."""

    status: HealthStatus
    timestamp: datetime
    gateway_connected: bool
    uptime_seconds: float
    version: str


@router.get("", response_model=HealthResponse)
async def health_check(
    health_checker: HealthChecker = Depends(get_health_checker),
    config: Config = Depends(get_config),
) -> HealthResponse:
    """Health check endpoint.

    Args:
        health_checker: Health checker instance (injected)
        config: Config instance (injected)

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
async def check_gateway(
    health_checker: HealthChecker = Depends(get_health_checker),
    config: Config = Depends(get_config),
) -> dict[str, bool | int]:
    """Check gateway connection status.

    Args:
        health_checker: Health checker instance (injected)
        config: Config instance (injected)

    Returns:
        Dictionary with gateway status
    """
    return {
        "connected": health_checker.gateway_connected,
        "consecutive_failures": health_checker.consecutive_failures,
        "threshold": config.health.unhealthy_threshold,
    }
```

### 5.4 Example Service with DI

**File: `app/services/scanner_service.py`** (refactored)

```python
"""Scanner service for orchestrating announcement scanning."""

from loguru import logger


class ScannerService:
    """Service for orchestrating announcement scanning."""

    def __init__(
        self,
        scanner: ASXPriceSensitiveScanner,
        notification_service: NotificationService,
        strategy_trigger_service: StrategyTriggerService,
    ) -> None:
        """Initialize scanner service.

        Args:
            scanner: Announcement scanner instance (injected)
            notification_service: Notification service instance (injected)
            strategy_trigger_service: Strategy trigger service instance (injected)
        """
        self.scanner = scanner
        self.notification_service = notification_service
        self.strategy_trigger_service = strategy_trigger_service

    async def scan(self) -> dict:
        """Run scanner and process announcements.

        Returns:
            Scan results dictionary
        """
        try:
            logger.info("Starting announcement scan")

            result = await self.scanner.fetch_announcements()

            if not result.success:
                logger.error(f"Scan failed: {result.error}")
                return {
                    "success": False,
                    "announcements": [],
                    "error": result.error,
                }

            announcements = result.announcements
            logger.info(f"Processing {len(announcements)} announcements")

            processed_count = 0

            for announcement in announcements:
                await self._process_announcement(announcement)
                processed_count += 1

            logger.info(f"Scan complete: processed {processed_count} announcements")

            return {
                "success": True,
                "announcements_count": len(announcements),
                "processed_count": processed_count,
            }

        except Exception as e:
            logger.error(f"Error during scan: {e}")
            return {
                "success": False,
                "announcements": [],
                "error": str(e),
            }

    async def _process_announcement(self, announcement) -> None:
        """Process a single announcement.

        Args:
            announcement: Announcement object
        """
        ticker = announcement.ticker
        headline = announcement.headline

        try:
            await self.notification_service.send_discord_webhook(
                ticker=ticker,
                headline=headline,
                timestamp=announcement.timestamp,
            )
        except Exception as e:
            logger.error(f"Failed to notify for {ticker}: {e}")

        try:
            await self.strategy_trigger_service.trigger_strategies(
                ticker=ticker,
                headline=headline,
            )
        except Exception as e:
            logger.error(f"Failed to trigger strategy for {ticker}: {e}")
```

## 6. Migration Plan

### 6.1 Phased Approach

#### Phase 1: Foundation (Week 1)
**Goal**: Set up container without disrupting existing code

 | File | Action | Impact |
 |------|--------|--------|
 | `app/container.py` | Create new file | No impact |
 | `app/main.py` | Add container initialization in lifespan | No impact |
 | `tests/test_container.py` | Create container tests | New test file |
 | `config/settings.yaml` | Remove `${VAR}` syntax, use empty strings | No impact |
 | `tests/test_config_loading.py` | Add config validation tests | New test file (see Section 8) |

#### Phase 2: API Routes (Week 1-2)
**Goal**: Migrate API routes to use Depends()

| File | Action | Impact |
|------|--------|--------|
| `app/api/v1/health/router.py` | Add Depends() parameters | No breaking change |
| `app/api/v1/historical_data/router.py` | Add Depends() parameters | No breaking change |
| `app/api/v1/scanner.py` | Add Depends() parameters | No breaking change |
| `app/api/v1/scanners/router.py` | Add Depends() parameters | No breaking change |
| `app/api/v1/announcement_gap/router.py` | Add Depends() parameters | No breaking change |

#### Phase 3: Services (Week 2-3)
**Goal**: Refactor services to receive dependencies via constructor

| File | Action | Impact |
|------|--------|--------|
| `app/services/gateway_service.py` | Remove global singleton, use container | Minor breaking change |
| `app/services/health_service.py` | Remove global singleton, use container | Minor breaking change |
| `app/services/notification_service.py` | Remove global, use factory | Minor breaking change |
| `app/services/strategy_trigger_service.py` | Remove global, use factory | Minor breaking change |
| `app/services/scanner_service.py` | Remove global, use factory | Minor breaking change |
| `app/services/announcement_gap_strategy_service.py` | Remove global, use factory | Minor breaking change |

#### Phase 4: Schedulers (Week 3)
**Goal**: Migrate schedulers to use container

| File | Action | Impact |
|------|--------|--------|
| `app/scheduler/import_scheduler.py` | Use container for services | Minor breaking change |
| `app/scheduler/scanner_scheduler.py` | Use container for services | Minor breaking change |

#### Phase 5: Main Entry Point (Week 3-4)
**Goal**: Update main.py to use container-managed services

| File | Action | Impact |
|------|--------|--------|
| `app/main.py` | Use container.get() instead of globals | Breaking change |
| `app/gateway.py` | Remove module-level singleton | Breaking change |
| `app/database.py` | Remove module-level singleton | Breaking change |
| `app/config.py` | Keep as-is (config is fine as module-level) | No change |

#### Phase 6: Cleanup (Week 4)
**Goal**: Remove deprecated code patterns

| File | Action | Impact |
|------|--------|--------|
| All service files | Remove `get_*_service()` functions | Breaking change |
| All modules | Remove direct singleton imports | Breaking change |
| `tests/` | Update all tests to use container | Test refactoring |

### 6.2 File-by-File Refactor Order

```
1. app/container.py                    (NEW)
2. tests/test_container.py            (NEW)
3. app/api/v1/health/router.py
4. app/api/v1/historical_data/router.py
5. app/api/v1/scanners/router.py
6. app/api/v1/scanner.py
7. app/api/v1/announcement_gap/router.py
8. app/services/health_service.py
9. app/services/gateway_service.py
10. app/services/strategy_service.py
11. app/services/notification_service.py
12. app/services/strategy_trigger_service.py
13. app/services/scanner_service.py
14. app/services/announcement_gap_strategy_service.py
15. app/scheduler/import_scheduler.py
16. app/scheduler/scanner_scheduler.py
17. app/scanner/scanner.py
18. app/scanner/announcement_gap_scanner.py
19. app/main.py
20. app/gateway.py
21. app/database.py
22. All test files
```

### 6.3 Rollback Strategy

Each phase is independently revertible:
1. Git branches per phase
2. Feature flags to enable/disable DI
3. Keep old `get_*()` functions as wrappers initially
4. Gradual migration with both paths working

## 7. Test Strategy

### 7.1 Unit Tests for Container

**File: `tests/test_container.py`**

```python
"""Test DI container."""

import pytest

from app.container import Container, get_container, reset_container


def test_singleton_registration():
    """Test singleton lifetime."""
    container = Container()
    container.singleton(DatabaseManager, DatabaseManager())
    instance1 = container.get(DatabaseManager)
    instance2 = container.get(DatabaseManager)
    assert instance1 is instance2


def test_transient_registration():
    """Test transient lifetime."""
    container = Container()
    from app.importer import CSVImporter
    container.transient(CSVImporter, CSVImporter)
    instance1 = container.get(CSVImporter)
    instance2 = container.get(CSVImporter)
    assert instance1 is not instance2


def test_factory_registration():
    """Test factory with parameters."""
    container = Container()
    from app.scanners.asx_price_sensitive import ScannerConfig, ASXPriceSensitiveScanner
    from app.config import config

    factory = lambda: ASXPriceSensitiveScanner(
        ScannerConfig(
            url=config.scanners.asx.url,
            timeout=config.scanners.asx.timeout,
            exclude_tickers=config.scanners.asx.exclude_tickers,
            min_ticker_length=config.scanners.asx.min_ticker_length,
            max_ticker_length=config.scanners.asx.max_ticker_length,
        )
    )
    container.factory(ASXPriceSensitiveScanner, factory)
    scanner = container.get(ASXPriceSensitiveScanner)
    assert scanner is not None


def test_override_for_testing():
    """Test test overrides."""
    from unittest.mock import Mock

    container = Container()
    container.singleton(DatabaseManager, DatabaseManager())

    mock_db = MockDatabaseManager()
    container.override(DatabaseManager, lambda: mock_db)

    result = container.get(DatabaseManager)
    assert isinstance(result, MockDatabaseManager)


def test_reset_overrides():
    """Test override cleanup."""
    from unittest.mock import Mock

    container = Container()
    container.singleton(DatabaseManager, DatabaseManager())

    container.override(DatabaseManager, lambda: Mock())
    container.reset_overrides()

    result = container.get(DatabaseManager)
    assert isinstance(result, DatabaseManager)


class MockDatabaseManager:
    """Mock database manager for testing."""
    pass
```

### 7.2 Integration Tests with DI

```python
"""Test API routes with dependency injection."""

from fastapi.testclient import TestClient

from app.main import app
from app.container import get_container
from app.services.health_service import HealthStatus
from unittest.mock import Mock


def test_health_check_endpoint():
    """Test health endpoint uses injected dependencies."""
    client = TestClient(app)
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data


def test_health_check_with_mock():
    """Test health endpoint with mocked dependencies."""
    mock_health_checker = Mock()
    mock_health_checker.get_status.return_value = HealthStatus.HEALTHY
    mock_health_checker.gateway_connected = True
    mock_health_checker.get_uptime.return_value = 100.0

    get_container().override(HealthChecker, lambda: mock_health_checker)

    client = TestClient(app)
    response = client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json()["status"] == "healthy"

    get_container().reset_overrides()
```

### 7.3 Test Coverage Goals

- Container unit tests: 100%
- API routes with DI: 90%+
- Services with DI: 80%+
- Integration tests for main.py startup: Full coverage

## 8. Config Loading Lessons Learned (Jan 2026)

### 8.1 The YAML Environment Variable Issue

**Problem Encountered:**
During CoolTrader login bug investigation, discovered that `settings.yaml` contained literal strings:
```yaml
cooltrader:
  username: "${COOLTRADER_USERNAME}"
  password: "${COOLTRADER_PASSWORD}"
```

**Root Cause:**
- Pydantic-settings loads configuration from multiple sources in priority order:
  1. Environment variables
  2. `.env` file
  3. Explicit values (including YAML loaded values)
- When YAML values are explicitly set (even if they're template strings), they **override** environment variables
- The `Config.from_yaml()` method was passing these literal strings directly to the Config class
- Result: `config.cooltrader.username` contained the literal string `"${COOLTRADER_USERNAME}"` not the env var value

**Fix Applied:**
```yaml
cooltrader:
  username: ""  # Empty string, lets env var take precedence
  password: ""
```

**Implications for DI Design:**
1. **Config cannot be a simple module-level singleton**
   - Module-level import happens before env vars are loaded
   - Need explicit config loading/validation step
   - Config should be in container to control lifecycle

2. **Need config validation tests**
   ```python
   def test_config_env_vars_loaded():
       os.environ["COOLTRADER_USERNAME"] = "test_user"
       config = load_config()
       assert config.cooltrader.username == "test_user"
       assert config.cooltrader.username != "${COOLTRADER_USERNAME}"
   ```

3. **DI container must handle config first**
   - Config should be the first registration in container
   - Services should get config via injection, not direct import
   - Config loading must happen at application startup, not module import

4. **YAML should be optional, not source of truth**
   - Environment variables should be the source of truth
   - YAML provides defaults only
   - No `${VAR}` template syntax - let pydantic-settings handle it

### 8.2 Updated Design Recommendations

**Change to Section 5.1:**
```python
def _initialize_container(container: Container) -> None:
    """Initialize container with all application dependencies."""
    from app.config import load_config, Config
    
    # Load and validate config explicitly
    config = load_config()
    container.singleton(Config, config)  # Config in container now!
    
    # Then register services that depend on config
    from app.database import DatabaseManager
    from app.gateway import GatewayManager
    
    container.singleton(DatabaseManager, DatabaseManager())
    container.singleton(GatewayManager, GatewayManager())
    # ... rest of services
```

**Change to Section 5.2:**
```python
def get_config() -> Config:
    """Get config from container."""
    return get_container().get(Config)

# No longer just "from app.config import config"
```

**New Test Requirement:**
```python
# tests/test_config_loading.py
def test_yaml_does_not_override_env_vars():
    """Ensure YAML defaults don't prevent env var loading."""
    os.environ["COOLTRADER_USERNAME"] = "env_user"
    os.environ["COOLTRADER_PASSWORD"] = "env_pass"
    
    config = load_config()
    assert config.cooltrader.username == "env_user"
    assert config.cooltrader.password == "env_pass"
    
    # Even if YAML has values, env vars win
    with open("config/settings.yaml") as f:
        yaml_content = yaml.safe_load(f)
    
    # If YAML had literal "${VAR}" values, that's a bug
    if yaml_content.get("cooltrader", {}).get("username", "").startswith("${"):
        pytest.fail("YAML contains unexpanded env var syntax")
```

## 9. Summary

### 9.1 Key Decisions

1. **Hybrid Approach**: FastAPI Depends() for routes + custom container for services
2. **Incremental Migration**: 6-week phased approach with rollback capability
3. **Zero External Dependencies**: Custom container implementation
4. **Preserve Behavior**: Gateway startup/shutdown, database, vn.py calls unchanged
5. **Config in Container**: Move Config from module-level to container-managed (based on Jan 2026 bug)
6. **Env Var Priority**: Environment > .env > YAML, not YAML literal strings

### 8.2 Expected Benefits

- **Testability**: Easy mocking of any dependency
- **Maintainability**: Clear dependency graph
- **Flexibility**: Easy to swap implementations
- **Code Quality**: Reduced global state, clearer interfaces

### 8.3 Risks and Mitigations

 | Risk | Probability | Impact | Mitigation |
 |------|-------------|--------|------------|
 | Breaking changes during migration | Medium | High | Feature flags, gradual migration |
 | Performance overhead | Low | Low | Minimal - singletons unchanged |
 | Learning curve for team | Medium | Medium | Documentation, code reviews |
 | Async compatibility issues | Low | Medium | Test async paths thoroughly |
 | **Config loading issues** | **Medium** | **High** | **Add config validation tests, verify env var loading (see notes below)** |
 | **Module-level config coupling** | **High** | **Medium** | **Move Config into container, not separate module-level singleton** |
| vn.py blocking call issues | Low | Medium | Keep existing run_in_executor pattern |

### 8.4 Success Criteria

1. All API routes use `Depends()` for dependencies
2. Zero module-level singletons except `config`
3. All tests pass with mocked dependencies
4. Zero performance regression
5. Team can write new code using DI patterns
