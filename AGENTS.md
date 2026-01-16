# AGENTS.md - Development Guidelines for Agentic Coding

This file contains essential information for agentic coding agents working in this repository.

## Build, Lint, and Test Commands

### Dependency Management
This project uses `uv` for fast dependency management.

```bash
# Install dependencies (dev mode includes test/lint tools)
uv sync --all-extras --dev

# Install production dependencies only
uv sync --all-extras --no-dev
```

### Code Quality Commands

```bash
# Format code
uv run ruff format app/

# Lint code
uv run ruff check app/

# Type checking
uv run mypy app/

# Run all checks (lint + type-check)
make check
# or
uv run ruff check app/ && uv run mypy app/

# Format, check, and test
make all
```

### Testing Commands

```bash
# Run all tests
uv run pytest

# Run tests with coverage
uv run pytest --cov=app --cov-report=term-missing --cov-report=html

# Run a single test file
uv run pytest tests/test_gateway.py

# Run a single test function
uv run pytest tests/test_gateway.py::test_connection

# Run tests with verbose output
uv run pytest -v

# Run tests matching a pattern
uv run pytest -k "test_gateway"
```

### Makefile Targets
```bash
make help        # Show all available targets
make install     # Install dependencies
make dev         # Install dev dependencies
make test        # Run tests
make lint        # Run linting
make format      # Format code
make type-check  # Run type checking
make check       # Run all checks
make build       # Build Docker image
make up          # Start Docker Compose
make down        # Stop Docker Compose
```

## Code Style Guidelines

### General Rules
- **Python Version**: 3.13+
- **Line Length**: 100 characters (strictly enforced by ruff)
- **No comments**: Code should be self-documenting (explicit request from maintainers)
- **Docstrings**: Required for all public classes, functions, and methods

### Import Organization
```python
# 1. Standard library imports
import asyncio
from pathlib import Path
from typing import Optional

# 2. Third-party imports
from fastapi import FastAPI
from loguru import logger
from pydantic import BaseModel

# 3. Local imports (from app package)
from app.config import config
from app.gateway import gateway_manager
```

### Type Hints
- All functions MUST have return type annotations
- Use Python 3.13 union syntax: `str | int | float` (not `Union[str, int]`)
- Use `dict[str, str]` instead of `Dict[str, str]`
- Use `list[Type]` instead of `List[Type]`
- Module-level variables should be typed: `gateway_manager: GatewayManager | None = None`
- Strict mypy mode is enabled: `disallow_untyped_defs = true`

### Naming Conventions

**Classes (PascalCase):**
```python
class IBGatewayConnection:
class StrategyManager:
class HealthResponse(BaseModel):
```

**Functions and Variables (snake_case):**
```python
def connect_to_gateway():
max_position_size = 100
```

**Module-level Constants (UPPER_SNAKE_CASE):**
```python
gateway_manager = GatewayManager()
health_checker = HealthChecker()
```

**Private Methods (_prefix):**
```python
def _connect_with_retry(self) -> None:
def _normalize_keys(data: dict) -> dict:
```

**Parameters**: Use descriptive names
```python
def send_order(self, req: OrderRequest) -> str:  # "req" is too short, prefer "order_request"
```

### Configuration Style
Use Pydantic v2 with pydantic-settings. All config classes inherit from `BaseSettings`.

```python
class TradingConfig(BaseSettings):
    max_position_size: int = Field(default=100, ge=1, description="Maximum position size")
    risk_per_trade: float = Field(default=0.02, ge=0, le=1, description="Risk percentage")

    @model_validator(mode="after")
    def validate_take_profit(self) -> "TradingConfig":
        if self.take_profit_pct <= self.stop_loss_pct:
            raise ValueError("Take profit must be greater than stop loss")
        return self
```

### Async/Await Patterns
- Use `asyncio` for async operations
- For blocking calls (like vn.py), use `run_in_executor`:
```python
await asyncio.get_event_loop().run_in_executor(
    None, lambda: self.main_engine.connect(setting, "IB")
)
```

### Error Handling
- Use specific exceptions (ConnectionError, ValueError, RuntimeError)
- Always log errors with context
- Re-raise exceptions after logging if necessary
```python
try:
    await gateway_manager.start()
except ConnectionError as e:
    logger.error(f"Failed to connect to IB Gateway: {e}")
    raise
```

### Logging
Use `loguru` for all logging:
```python
logger.info("Starting application...")
logger.warning("Gateway disconnected, attempting to reconnect...")
logger.error(f"Failed to connect: {error}")

# Structured logging for production
logger.add(
    sys.stdout,
    level=log_level,
    serialize=True,  # JSON format
)
```

### Docstring Format (Google Style)
```python
def connect(self) -> None:
    """Connect to IB Gateway.

    Raises:
        ConnectionError: If connection fails after retries
    """
```

### FastAPI Endpoints
- Use `APIRouter` with `prefix` and `tags`
- Use Pydantic models for request/response
- Include proper error handling:
```python
@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Health check endpoint.

    Returns:
        HealthResponse with current status
    """
    return HealthResponse(...)
```

### Strategy Development
Inherit from `BaseCtaStrategy` and implement abstract methods:
```python
class MyStrategy(BaseCtaStrategy):
    def _setup_parameters(self) -> None:
        self.fast_period: int = 10

    def on_init(self) -> None:
        # Initialize indicators, BarGenerator, etc.
        pass

    def on_bar(self, bar: BarData) -> None:
        # Process bar data
        pass
```

### ASX Symbol Format
vn.py symbols use format: `{SYMBOL}.{CURRENCY}-{TYPE}-{EXCHANGE}`
```python
# ASX direct routing (recommended)
vt_symbol = "BHP-STK-ASX"
vt_symbol = "CBA-STK-ASX"

# US stocks (SMART routing)
vt_symbol = "AAPL-STK-SMART"
```

### Testing Patterns
Tests should be in `tests/` directory with `test_` prefix:
```python
import pytest

from app.config import config


def test_config_defaults():
    assert config.trading.max_position_size == 100


@pytest.mark.asyncio
async def test_gateway_connection():
    # Test async functionality
    pass
```

### Important Notes
1. **Always run `make all` before committing** (formats, lints, type-checks, and tests)
2. **NEVER commit secrets** (.env is in .gitignore)
3. **Docker for development**: Use `docker compose up -d` for running services
4. **Health checks**: Expose endpoints at `/health`, `/health/ready`, `/health/live`
5. **Retry logic**: Use `tenacity` for retrying network operations
6. **Type safety**: mypy is strict - all code must pass type checking
7. **Coverage**: Aim for high test coverage (pytest-cov is configured)

### Common Patterns

**Context managers for async lifecycle:**
```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    await startup()
    yield
    await shutdown()
```

**Validators in Pydantic models:**
```python
@field_validator("field_name")
@classmethod
def validate_field(cls, v: str) -> str:
    # Validation logic
    return v
```

**Handling optional dependencies:**
```python
from typing import Optional

def get_connection(self) -> Optional[IBGatewayConnection]:
    return self.connection
```
