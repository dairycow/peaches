# AGENTS.md - Development Guidelines

## Language
- Use Australian English spelling (e.g., colour, analyse, initialise, organise)
- No emojis in documentation or code

## Build/Lint/Test Commands

```bash
uv sync --all-extras              # Install dependencies
make format                       # Format with ruff
make lint                         # Lint with ruff
make type-check                   # Type check with mypy
make check                        # All checks (lint + type-check)
make test                         # Unit tests only
make test-integration             # Integration tests
make test-all                     # All tests
uv run pytest tests/test_file.py  # Single test file
uv run pytest tests/test_file.py::test_fn  # Single test function
uv run pytest -k "pattern"        # Pattern match
```

## Code Style

### Formatting & Imports
- Python 3.13+, line length 100 chars
- No inline comments - code should be self-documenting
- Docstrings required for public APIs

```python
# Import order: stdlib → third-party → local
import asyncio
from typing import TYPE_CHECKING, Any

from fastapi import APIRouter
from loguru import logger
from pydantic import BaseModel, Field

from app.config import config

if TYPE_CHECKING:
    from app.services.scanner_service import ScannerService
```

### Type Hints
```python
def process_data(items: list[str]) -> dict[str, int]: ...
result: str | None = None
_service: Service | None = None
```

### Naming Conventions
- `PascalCase`: classes (e.g., `ScannerService`)
- `snake_case`: functions/variables (e.g., `process_announcement`)
- `UPPER_SNAKE_CASE`: constants (e.g., `MAX_RETRIES`)
- `_prefix`: private members (e.g., `_event_bus`)

### Error Handling
```python
class IBKRWebAPIError(Exception):
    """Base exception for IBKR web API errors."""

try:
    await operation()
except ConnectionError as e:
    logger.error(f"Connection failed: {e}", exc_info=True)
    raise

with contextlib.suppress(asyncio.CancelledError):
    await task
```

### Logging
```python
from loguru import logger  # Always use loguru, never standard logging

logger.info("Message")
logger.error(f"Error: {error}", exc_info=True)
```

## Architecture Patterns

### Service Layer (Singleton)
```python
# container.py - dependency injection
_service: Service | None = None

def get_service() -> Service:
    global _service
    if _service is None:
        _service = Service()
    return _service
```

### FastAPI Routers
```python
router = APIRouter(prefix="/resource", tags=["resource"])

class ResponseModel(BaseModel):
    status: str

@router.get("", response_model=ResponseModel)
async def get_resource() -> ResponseModel:
    return ResponseModel(status="ok")
```

### Event-Driven Communication
```python
@dataclass
class ScanStartedEvent(Event):
    source: str

await event_bus.publish(ScanStartedEvent(source="manual"))
await event_bus.subscribe(ScanStartedEvent, self._handle_scan)
```

### Configuration
```python
class Config(BaseSettings):
    model_config = SettingsConfigDict(
        env_nested_delimiter="__",
        case_sensitive=False,
        env_file=".env",
    )
    field: str = Field(default="value", description="Description")
```

## Testing

```python
import pytest

def test_creation():
    assert Service() is not None

@pytest.mark.asyncio
async def test_async_operation():
    result = await service.process()
    assert result.success

@pytest.mark.integration
@pytest.mark.asyncio
async def test_database_connection():
    ...
```

- Test business logic, not frameworks
- Avoid mocks for FastAPI - use real components
- Reset singletons between tests

## Key Files

| File | Purpose |
|------|---------|
| `app/config.py` | Pydantic Settings |
| `app/container.py` | Dependency injection |
| `app/main.py` | FastAPI app and lifespan |
| `app/events/bus.py` | Event-driven communication |
| `app/services/` | Business logic |

## Important Notes

1. Run `make check` before committing
2. Never commit secrets (.env is in .gitignore)
3. Use `TYPE_CHECKING` for circular import avoidance
4. Use `loguru` for all logging
5. Use modern syntax: `list[str]` not `List[str]`, `X | None` not `Optional[X]`
