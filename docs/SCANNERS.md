# Market Scanners

## Runtime Scanners (Live Trading)

### ASX Price-Sensitive Scanner

**File**: `app/scanners/asx_price_sensitive.py:36`

Scans ASX announcements for price-sensitive information.

**What It Detects**:
- Price-sensitive announcements from ASX
- Filters by ticker length (3-6 characters)
- Excludes specific tickers (TEST, DEMO)

**Configuration**:

| Parameter | Default | Description |
|-----------|---------|-------------|
| `url` | ASX URL | Announcements endpoint |
| `timeout` | 10 seconds | Request timeout |
| `exclude_tickers` | TEST, DEMO | Tickers to skip |
| `min_ticker_length` | 3 | Minimum ticker length |
| `max_ticker_length` | 6 | Maximum ticker length |

**Usage**:
```python
from app.scanners.asx_price_sensitive import (
    ASXPriceSensitiveScanner,
    ScannerConfig,
)

config = ScannerConfig(
    url="https://www.asx.com.au/asx/v2/statistics/todayAnns.do",
    timeout=10,
    exclude_tickers=["TEST", "DEMO"],
    min_ticker_length=3,
    max_ticker_length=6,
)

scanner = ASXPriceSensitiveScanner(config)
result = await scanner.fetch_announcements()
```

**API Endpoints**:
- `POST /api/v1/scanners/trigger` - Manual scan trigger
- `GET /api/v1/scanners/status` - Scanner status

**Schedule**: 10:00:30 AM AEST weekdays (configurable via `scanners.asx.scan_schedule`)

## Analysis Scanners (Backtesting)

### Gap Scanner

**File**: `app/analysis/scanners/gap_scanner.py:10`

Identifies significant price gaps in historical data.

**What It Detects**:
- Price gaps exceeding threshold percentage
- Confirmed by high volume (multiple of 50-day average)
- Minimum daily volume requirement

**Parameters**:

| Parameter | Default | Description |
|-----------|---------|-------------|
| `gap_threshold` | 10.0 | Minimum gap percentage |
| `volume_multiplier` | 2.0 | Volume multiple vs 50-day avg |
| `min_volume` | 50000 | Minimum daily volume |

**CLI Usage**:
```bash
uv run python -c "
from app.cli.analysis_cli import cli
import sys
sys.argv = ['peaches-analysis', 'scanner', 'gaps', 
           '--start-date', '2024-01-01', '--end-date', '2024-12-31',
           '--gap-threshold', '10.0']
cli()
"
```

### Momentum Scanner

**File**: `app/analysis/scanners/momentum_scanner.py:8`

Detects momentum bursts and consolidation patterns.

**What It Detects**:

**Momentum Bursts**:
- 3+ consecutive up days (configurable)
- Calculates total gain percentage
- Tracks volume spikes vs baseline

**Consolidation Patterns**:
- Flat price movement (max 10% range)
- Low volume vs historical baseline
- Minimum 5 days duration

**Parameters**:

| Parameter | Default | Description |
|-----------|---------|-------------|
| `min_days` | 3 | Minimum consecutive up days |
| `max_range_pct` | 10.0 | Max price range for consolidation |
| `volume_threshold` | 0.5 | Volume ratio threshold (50% of baseline) |

**CLI Usage**:
```bash
# Scan for momentum bursts
uv run python -c "
from app.cli.analysis_cli import cli
import sys
sys.argv = ['peaches-analysis', 'scanner', 'momentum', 
           '--start-date', '2024-01-01', '--end-date', '2024-12-31',
           '--min-days', '3']
cli()
"

# Scan for consolidations
uv run python -c "
from app.cli.analysis_cli import cli
import sys
sys.argv = ['peaches-analysis', 'scanner', 'consolidation', 
           '--start-date', '2024-01-01', '--end-date', '2024-12-31',
           '--max-range-pct', '10.0']
cli()
"
```

## Announcement Gap Scanner

The announcement gap strategy includes its own scanner service:

**File**: `app/services/announcement_gap_strategy_service.py`

**What It Detects**:
- Stocks with price-sensitive announcements
- Positive gap percentage
- Price above 6-month high
- Price above minimum threshold

**API Endpoints**:
- `POST /api/v1/announcement-gap/scan` - Scan for gap candidates
- `POST /api/v1/announcement-gap/sample-opening-ranges` - Scan with opening range sampling

**Parameters**:

| Parameter | Default | Description |
|-----------|---------|-------------|
| `min_price` | 0.20 | Minimum stock price |
| `min_gap_pct` | 0.0 | Minimum gap percentage |
| `lookback_months` | 6 | Lookback for high calculation |

## Configuration

All scanners configured in `app/config.py`:

```bash
# ASX scanner configuration
SCANNERS__ENABLED=true
SCANNERS__ASX__URL="https://www.asx.com.au/asx/v2/statistics/todayAnns.do"
SCANNERS__ASX__SCAN_SCHEDULE="30 10 * * 1-5"
SCANNERS__ASX__TIMEOUT=10

# Gap scanner configuration
SCANNER__GAP_THRESHOLD=3.0
SCANNER__MIN_PRICE=1.0
SCANNER__MIN_VOLUME=100000
SCANNER__MAX_RESULTS=50
SCANNER__OPENING_RANGE_TIME="10:05"
SCANNER__TIMEZONE="Australia/Sydney"
SCANNER__ENABLE_SCANNER=false
```

## Related Files

- Runtime scanners: `app/scanners/`, `app/scanner/`
- Analysis scanners: `app/analysis/scanners/`
- Scanner services: `app/services/scanner_service.py`
- Announcement gap service: `app/services/announcement_gap_strategy_service.py`
- CLI interface: `app/cli/analysis_cli.py`
