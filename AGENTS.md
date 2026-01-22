# AGENTS.md - Development Guidelines

## Language
- Use Australian English spelling (e.g., colour, analyse, initialise, organise)
- No emojis in documentation

## Development Workflow

### Git Worktree Development
Worktrees are used for feature development, keeping main clean.

```bash
# Create a new worktree (from ~/peaches)
./create-worktree.sh feature/new-feature

# Work in worktree at ~/peaches-feature-new-feature/
# - Has its own venv (uv venv + uv sync --group dev)
# - data-prod symlink → /opt/peaches/data
# - logs-prod symlink → /opt/peaches/logs

# When done: merge back and cleanup
./merge-worktree.sh feature/new-feature
# This merges to main, pushes to origin, and cleans up worktree
```

### Deployment
Deploy to production from `/opt/peaches`:

```bash
cd /opt/peaches
./manual-deploy.sh
```

Deployment:
- Pulls latest from `origin/main` (use `merge-worktree.sh` to push first)
- Validates secrets and env vars
- Rebuilds Docker images
- Restarts containers
- Waits for health checks

## Code Quality

### Commands
```bash
# Format
uv run ruff format app/

# Lint
uv run ruff check app/

# Type check
uv run mypy app/

# Test
uv run pytest

# All checks
make check
```

### Style Guidelines
- **Python**: 3.13+
- **Line length**: 100 chars (ruff enforced)
- **No comments**: Code should be self-documenting
- **Docstrings**: Required for public APIs

### Type Hints
```python
def process_data(input: str) -> dict[str, int]:
    return {"count": len(input)}

module_var: str | None = None
```

### Naming
- Classes: `PascalCase`
- Functions/variables: `snake_case`
- Constants: `UPPER_SNAKE_CASE`
- Private: `_prefix`

## Code Patterns

### Configuration
```python
from pydantic_settings import BaseSettings

class Config(BaseSettings):
    field: str = Field(default="value", description="Description")
```

### Async
```python
# Use run_in_executor for blocking vn.py calls
await asyncio.get_event_loop().run_in_executor(
    None, lambda: self.engine.connect(setting, "IB")
)
```

### Error Handling
```python
try:
    await operation()
except ConnectionError as e:
    logger.error(f"Connection failed: {e}")
    raise
```

### Logging
```python
from loguru import logger
logger.info("Message")
logger.warning("Warning")
logger.error(f"Error: {error}")
```

## FastAPI

### Router Structure
```python
from fastapi import APIRouter
router = APIRouter(prefix="/api/v1/resource", tags=["resource"])

@router.get("/endpoint")
async def endpoint() -> ResponseModel:
    return ResponseModel()
```

### Response Models
```python
class ResponseModel(BaseModel):
    field: str
    count: int
```

## Database & Data

### CSV Import
- Config: `config.historical_data.csv_dir` (default: `/app/data/raw/cooltrader`)
- CSV format: `symbol,date,open,high,low,close,volume`
- Date format: `%d/%m/%Y`

### Data Access
```python
from app.database import get_database_manager

db = get_database_manager()
db.save_bars(bars_list)
stats = db.get_database_stats()
```

## API Endpoints

### Health
- `GET /api/v1/health` - Service health
- `GET /api/v1/health/ready` - Readiness
- `GET /api/v1/health/live` - Liveness

### Data Import
- `POST /api/v1/import/import/trigger` - Trigger CSV import
- `GET /api/v1/import/database/stats` - DB statistics
- `GET /api/v1/import/database/overview` - Symbol overview
- `POST /api/v1/import/schedule/start` - Start scheduler
- `POST /api/v1/import/schedule/stop` - Stop scheduler

## Testing

### Philosophy
Test business logic, not frameworks. Avoid mocks for vn.py/FastAPI.

### Commands
```bash
# All tests
uv run pytest

# With coverage
uv run pytest --cov=app --cov-report=term-missing

# Single file
uv run pytest tests/test_file.py

# Single test
uv run pytest tests/test_file.py::test_function

# Pattern match
uv run pytest -k "test_import"
```

## Important Notes

1. **Always run checks before committing**: `make check`
2. **Never commit secrets** (.env is in .gitignore)
3. **Worktrees provide isolation** - separate venv, symlinked data/logs
4. **Health checks required** - all services must be healthy
5. **Type hints encouraged** but type checking is relaxed
6. **Avoid mocks** - prefer real components
7. **Track AI mistakes** - use `/capture-mistakes` to document and learn from AI-generated mistakes

## AI Mistake Tracking

### docs/MISTAKES.md
Maintains a chronological log of AI-generated mistakes to prevent recurrence.

### Capture Workflow
Use `/capture-mistakes` command to automatically:
- Analyse recent AI-generated changes
- Identify common Python pattern violations
- Categorise mistakes by severity (INFO/WARNING/ERROR)
- Append structured entries to docs/MISTAKES.md

### Mistake Categories
- **Code patterns**: Async violations, error handling, type hints, style issues
- **Testing**: Missing tests, improper mocking, test failures
- **Documentation**: Missing docstrings, outdated comments

### Severity Levels
- **INFO**: Style violations, minor issues, recommendations
- **WARNING**: Potential issues, non-critical bugs
- **ERROR**: Blocking issues, test failures, deployment failures

## Configuration Files

- `.env` - Environment variables
- `config/settings.yaml` - App configuration
- `docker-compose.yml` - Service definitions
- `.opencode/opencode.json` - OpenCode permissions
