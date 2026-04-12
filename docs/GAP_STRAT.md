# Announcement Gap Breakout Strategy Documentation

## Executive Summary

The **Announcement Gap Breakout Strategy** is an ASX-focused momentum strategy that capitalises on price gaps following price-sensitive announcements. The strategy identifies stocks that have made announcements, gapped up positively, and broken through their 6-month high, entering after a 5-minute opening range breakout.

**Status**: Strategy code exists but is NOT currently loaded in the CTA engine. It operates in scan-only mode via announcement tracking.

---

## Strategy Overview

### Core Logic

```python
# Entry Conditions (all must be true):
1. Stock made a price-sensitive announcement today (within 24 hours)
2. Positive gap from previous close (gap_pct >= min_gap_pct)
3. Current price > 6-month high
4. Stock price >= min_price ($0.20 default)
5. Time >= 10:05 AM AEST (5-minute opening range set)

# Execution:
- Place market stop order at opening range high (ORH)
- Stop loss set to day low
- Position size: 100 shares (default)

# Exit Conditions:
- Time-based exit after 3 days
- No take profit target
```

### Strategy Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `min_price` | 0.20 | Minimum stock price threshold |
| `min_gap_pct` | 0.0 | Minimum gap percentage (0 = any positive gap) |
| `lookback_months` | 6 | Lookback period for high calculation |
| `opening_range_minutes` | 5 | Opening range duration (minutes) |
| `position_size` | 100 | Number of shares per trade |
| `max_positions` | 10 | Maximum concurrent positions |
| `exit_days` | 3 | Days to hold before exit |

---

## System Architecture

### High-Level Architecture

```
+---------------------------+     +--------------------------------+
| External Data Sources     |     | Peaches Bot Container          |
|                           |     |                                |
| ASX Website               |     | Scanner Layer                  |
| todayAnns.do              | --> |  ASX Price-Sensitive Scanner   |
|                           |     |  ScannerScheduler              |
|                           |     |   Cron: 30 10 * * 1-5          |
|                           |     |  AnnouncementGapScanner       |
|                           |     |                                |
|                           |     | Strategy Layer                 |
|                           |     |  AnnouncementGapBreakout       |
|                           |     |  ANNOUNCEMENT_TRACKER          |
|                           |     |                                |
|                           |     | API Layer                      |
|                           |     |  FastAPI Port 8080             |
|                           |     |  AnnouncementGap Router        |
|                           |     |                                |
|                           |     | Database                      |
|                           |     |  SQLite (trading.db)           |
+---------------------------+     +--------------------------------+
```

### Docker Infrastructure

```yaml
# docker-compose.yml
services:
  peaches-bot:
    build: .
    ports: ["127.0.0.1:8080:8080"]
    healthcheck:
      test: curl -f http://localhost:8080/api/v1/health
    volumes:
      - ./data:/app/data
      - ./logs:/app/logs
```

**Volumes**:
- `./data:/app/data` - Data storage (historical, trading)
- `./logs:/app/logs` - Logs

---

## Process Flow

### Startup Sequence

1. Container starts
2. `startup()` runs
3. EventBus starts
4. Strategy service initialises (only ASXMomentumStrategy loaded)
5. ScannerScheduler starts
6. Application ready

### Daily Scan Flow (Announcement Registration)

```
10:00:30 AM AEST weekdays
    |
    v
ASXScanner.fetch_announcements()
    |
    v
Fetch from ASX website
Parse HTML, filter "pricesens"
    |
    v
For each announcement:
    +-> Send Discord webhook notification
    +-> GapScanner.scan_candidates()
        +-> Load bars from DB
        +-> Check gap, 6M high, price
        +-> If candidate passes all filters:
            +-> register_announcement(symbol, time)
                (Added to ANNOUNCEMENT_TRACKER)
```

### API Trigger Flow (Manual Scan)

```
POST /api/v1/announcement-gap/scan
    |
    v
GapService.get_announcement_gap_strategy_service()
    |
    v
ASXScanner.fetch_announcements()
    |
    v
GapScanner.scan_candidates()
    +-> Evaluate each symbol
    +-> If candidate passes:
        +-> register_announcement(symbol, time)
    |
    v
ScanResponse (candidates list)
```

---

## Entry Points and Initialization

### Code Entry Points

| Entry Point | File | Purpose |
|-------------|------|---------|
| `main:app` | `app/main.py` | FastAPI application (uvicorn entry) |
| `AnnouncementGapBreakoutStrategy` | `app/strategies/announcement_gap_strategy.py:66` | Strategy class |
| `register_announcement()` | `app/strategies/announcement_gap_strategy.py:25` | Global registration function |
| `check_announcement_today()` | `app/strategies/announcement_gap_strategy.py:36` | Check for recent announcement |
| `run_scan()` | `app/scheduler/scanner_scheduler.py:84` | Scheduled scan job |
| `scan_candidates()` | `app/scanners/gap/announcement_gap_scanner.py` | Candidate scanner |

### Current Strategy Loading Status

**File**: `app/services/strategy_service.py:31-36`

```python
cta_engine.add_strategy(
    "ASXMomentumStrategy",  # Only this strategy is loaded
    STRATEGY_NAME,
    VT_SYMBOL,
    DEFAULT_PARAMETERS,
)
```

**Result**: `AnnouncementGapBreakoutStrategy` is NOT loaded into the CTA engine. It cannot actively trade.

---

## Configuration

### Settings (app/config.py)

```bash
# Gap scanner configuration
SCANNER__GAP_THRESHOLD=3.0
SCANNER__MIN_PRICE=1.0
SCANNER__MIN_VOLUME=100000
SCANNER__MAX_RESULTS=50
SCANNER__OPENING_RANGE_TIME="10:05"
SCANNER__ENABLE_SCANNER=false

# ASX scanner configuration
SCANNERS__ENABLED=true
SCANNERS__ASX__SCAN_SCHEDULE="30 10 * * 1-5"
SCANNERS__ASX__URL="https://www.asx.com.au/asx/v2/statistics/todayAnns.do"
SCANNERS__ASX__TIMEOUT=10

# Strategy triggers
SCANNERS__TRIGGERS__ENABLED=true
SCANNERS__TRIGGERS__STRATEGIES="asx_momentum"
```

### Strategy Default Parameters

**File**: `app/strategies/announcement_gap_strategy.py:55-63`

```python
DEFAULT_PARAMETERS = {
    "min_price": 0.20,
    "min_gap_pct": 0.0,
    "lookback_months": 6,
    "opening_range_minutes": 5,
    "position_size": 100,
    "max_positions": 10,
    "exit_days": 3,
}
```

---

## Data Flow

### Announcement Tracking

```
ASX Scanner -> Gap Scanner -> Candidate passes filters -> register_announcement
    -> ANNOUNCEMENT_TRACKER (dict[symbol, datetime])
    -> Strategy checks entry -> check_announcement_today
    -> symbol in tracker & < 24h -> Return True
```

### Database Access

```
Gap Scanner -> SQLite Database
Strategy -> SQLite Database

Tables:
  BarData (symbol, interval, open, high, low, close, volume)
```

---

## API Endpoints

### Announcement Gap Strategy API

**Base Path**: `/api/v1/announcement-gap`

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/scan` | Scan for announcement gap candidates |
| POST | `/sample-opening-ranges` | Scan and sample opening ranges |

#### POST /api/v1/announcement-gap/scan

**Request**:
```json
{
  "min_price": 0.20,
  "min_gap_pct": 0.0,
  "lookback_months": 6
}
```

**Response**:
```json
{
  "success": true,
  "candidates_count": 2,
  "candidates": [
    {
      "symbol": "BHP",
      "gap_pct": 2.5,
      "six_month_high": 48.50,
      "current_price": 49.75,
      "announcement_headline": "Quarterly Report",
      "announcement_time": "2026-01-22T10:00:30",
      "exchange": "LOCAL"
    }
  ],
  "message": "Found 2 candidates"
}
```

### Scanner Control API

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/scanners/trigger` | Manual trigger for ASX scan |
| GET | `/api/v1/scanners/status` | Scanner status |

---

## Important Questions and Answers

### Q: Will this strategy just work now?

**A: NO.** Here's why:

1. **Not loaded in CTA Engine**: `strategy_service.py` only loads `ASXMomentumStrategy`. The announcement gap strategy is never initialised or started.

2. **No real-time market data**: The strategy requires live bar data (`on_bar()` callbacks).

3. **Missing strategy instance**: `AnnouncementGapBreakoutStrategy` must be added to the CTA engine with a `vt_symbol`.

4. **No multi-symbol support**: The current implementation is single-symbol. To scan multiple symbols, you'd need one strategy instance per symbol.

### Q: What parts are currently working?

**A: Only the scanning/candidate identification part**:

- ASX announcement scanner runs daily at 10:00:30 AM AEST
- `AnnouncementGapScanner` evaluates candidates against filters
- `register_announcement()` populates `ANNOUNCEMENT_TRACKER`
- API endpoints work for manual scanning

### Q: What are the dependencies?

**A: External and internal dependencies**:

**External**:
- ASX website (todayAnns.do) for announcements
- CoolTrader for historical bar data
- SQLite database for historical bar data

**Internal**:
- Loguru for logging
- BeautifulSoup for HTML parsing

### Q: What are the limitations?

**A: Known limitations**:

1. **In-memory tracker**: `ANNOUNCEMENT_TRACKER` is lost on restart. No persistence.

2. **Single-instance design**: Strategy designed for one symbol. Not production-ready for multi-symbol scanning.

3. **No position sizing logic**: Fixed 100 shares, ignores account balance.

4. **No risk management**: No max drawdown, daily loss limits, or position correlation checks.

5. **Timezone assumptions**: Hard-coded AEST (Australia/Sydney). May not work in other regions.

6. **Opening range calculation**: Assumes 10:00 AM market open. ASX opens at 10:00 AM AEST.

### Q: How to test the strategy?

**A: Testing approaches**:

1. **Manual scan via API**:
    ```bash
    curl -X POST http://localhost:8080/api/v1/announcement-gap/scan \
      -H "Content-Type: application/json" \
      -d '{"min_price": 0.20, "min_gap_pct": 0.0, "lookback_months": 6}'
    ```

2. **Backtesting**: Use peaches-analysis CLI

3. **Check logs**:
    ```bash
    docker logs peaches-bot
    ```

---

## Key Files Reference

| File | Purpose |
|------|---------|
| `app/strategies/announcement_gap_strategy.py` | Strategy implementation |
| `app/scanners/gap/announcement_gap_scanner.py` | Candidate scanner |
| `app/scanners/asx/asx_price_sensitive.py` | ASX announcement fetcher |
| `app/scheduler/scanner_scheduler.py` | Scheduled scan job |
| `app/services/strategy_service.py` | CTA engine (strategy loading) |
| `app/services/announcement_gap_strategy_service.py` | Gap strategy orchestration service |
| `app/api/v1/announcement_gap/router.py` | API endpoints |
| `docker-compose.yml` | Docker infrastructure |
| `app/config.py` | Configuration |

---

## Summary

The Announcement Gap Breakout Strategy is a well-designed momentum strategy with complete logic for scanning, filtering, and trading. However, it is **not currently trading**:

- **Working parts**: ASX scanner, candidate filtering, announcement tracking, API endpoints
- **Missing parts**: Strategy loading into CTA engine, market data subscription, multi-symbol support

The strategy is production-ready from a code quality standpoint but requires integration work to become an active trading system.
