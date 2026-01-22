# Internal Services

## Service Architecture

Peaches uses a service-oriented architecture with specialised services for gateway, health, scanning, notifications, and strategy triggering.

## Core Services

### Gateway Service

**File**: `app/services/gateway_service.py:12`

Manages IB Gateway connection lifecycle.

**Responsibilities**:
- Initialise IB Gateway connection
- Monitor connection health
- Auto-reconnect on failure
- Health check loop

**Methods**:

| Method | Description |
|--------|-------------|
| `start()` | Initialise IB Gateway connection |
| `stop()` | Stop IB Gateway connection |
| `health_check_loop()` | Run periodic health checks |

**Usage**:
```python
from app.services.gateway_service import gateway_service

await gateway_service.start()
# ... application runs ...
await gateway_service.stop()
```

### Health Service

**File**: `app/services/health_service.py:9`

Monitors application health and gateway status.

**Responsibilities**:
- Track gateway connection status
- Count consecutive failures
- Calculate health status (healthy, degraded, unhealthy)
- Track uptime

**Health Statuses**:
- `HEALTHY` - Gateway connected, no recent failures
- `DEGRADED` - Gateway disconnected but within failure threshold
- `UNHEALTHY` - Exceeded consecutive failure threshold

**Methods**:

| Method | Description |
|--------|-------------|
| `set_gateway_status(connected)` | Update gateway status |
| `get_status()` | Get current health status |
| `get_uptime()` | Get application uptime in seconds |

**API Endpoints**:
- `GET /api/v1/health` - Overall health status
- `GET /api/v1/health/gateway` - Gateway connection details
- `GET /api/v1/health/ready` - Readiness check
- `GET /api/v1/health/live` - Liveness check

### Scanner Service

**File**: `app/services/scanner_service.py:11`

Orchestrates announcement scanning and processing.

**Responsibilities**:
- Run ASX announcement scanner
- Process each announcement
- Send notifications
- Trigger strategies

**Workflow**:
1. Fetch announcements from ASX
2. For each announcement:
   - Send Discord notification
   - Trigger registered strategies
3. Return scan results

**Methods**:

| Method | Description |
|--------|-------------|
| `scan()` | Run scanner and process announcements |

**Usage**:
```python
from app.services.scanner_service import get_scanner_service

scanner_service = get_scanner_service(
    scanner=asx_scanner,
    notification_service=discord_service,
    strategy_trigger_service=trigger_service,
)
result = await scanner_service.scan()
```

### Strategy Trigger Service

**File**: `app/services/strategy_trigger_service.py:11`

Triggers trading strategies based on announcements.

**Responsibilities**:
- Manage enabled strategies list
- Call `on_announcement` methods on strategy modules
- Handle strategy import errors gracefully

**Methods**:

| Method | Description |
|--------|-------------|
| `trigger_strategies(ticker, headline)` | Trigger all enabled strategies |

**Configuration**:
```yaml
scanners:
  triggers:
    enabled: true
    strategies:
      - "asx_momentum"
```

### Notification Service

**File**: `app/services/notification_service.py`

Sends notifications via Discord webhooks.

**Responsibilities**:
- Format announcement messages
- Send to Discord webhook
- Handle notification errors

**Configuration**:
```yaml
scanners:
  notifications:
    discord:
      enabled: true
      webhook-url: "${DISCORD_WEBHOOK_URL}"
      username: "peaches-bot"
```

### Announcement Gap Strategy Service

**File**: `app/services/announcement_gap_strategy_service.py`

Service for announcement gap strategy scanning.

**Responsibilities**:
- Scan for announcement gap candidates
- Sample opening ranges for candidates
- Filter by price, gap, 6-month high

**Methods**:

| Method | Description |
|--------|-------------|
| `run_daily_scan()` | Scan for gap candidates |
| `scan_and_sample_opening_ranges()` | Scan with opening range sampling |

**API Endpoints**:
- `POST /api/v1/announcement-gap/scan` - Scan for gap candidates
- `POST /api/v1/announcement-gap/sample-opening-ranges` - Scan with opening range sampling

### Strategy Service

**File**: `app/services/strategy_service.py`

Base strategy service (extension point for future strategy management).

## Service Coordination

**Startup Sequence**:
1. Health service initialises
2. Gateway service starts IB Gateway
3. Scanner service configured with notification and trigger services
4. Scheduler services start periodic scans

**Runtime Flow**:
```
Scanner Scheduler
    ↓
Scanner Service
    ├→ Announcement Scanner
    ├→ Notification Service (Discord)
    └→ Strategy Trigger Service
          └→ Strategy Modules
```

## Configuration

All services configured in `config/settings.yaml`:

```yaml
gateway:
  host: "ib-gateway"
  port: 4004
  client-id: 1
  connect-timeout: 30
  auto-reconnect: true
  reconnect-interval: 5
  max-reconnect-attempts: 10

health:
  enabled: true
  interval-seconds: 30
  gateway-timeout: 5
  unhealthy-threshold: 3

scanners:
  enabled: true
  asx:
    scan-schedule: "30 10 * * 1-5"
  notifications:
    discord:
      enabled: true
  triggers:
    enabled: true
```

## Related Files

- Gateway: `app/gateway.py`, `app/gateway_scanner.py`
- Scanner: `app/scanner/`, `app/scanners/`
- Strategies: `app/strategies/`, `app/analysis/strategies/`
- Configuration: `app/config.py`, `config/settings.yaml`
