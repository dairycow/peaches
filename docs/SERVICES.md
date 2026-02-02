# Internal Services

## Architecture Overview

Peaches uses a **service-oriented architecture** with **event-driven communication**.

- **Services Layer**: Core business logic (GatewayService, NotificationService, etc.)
- **Event Handlers Layer**: Coordinate services via EventBus
- **EventBus**: Async publish/subscribe for decoupled communication

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

### Notification Service

**File**: `app/services/notification_service.py:11`

Sends notifications via Discord webhooks. Used by DiscordHandler.

**Responsibilities**:
- Format announcement messages
- Send to Discord webhook
- Handle notification errors

**Configuration**:
```bash
# Environment variables
DISCORD__ENABLED=true
DISCORD__WEBHOOK_URL="https://discord.com/api/webhooks/..."
DISCORD__USERNAME="peaches-bot"
```

### Strategy Trigger Service

**File**: `app/services/strategy_trigger_service.py:11`

Triggers trading strategies based on announcements. Used by StrategyHandler.

**Responsibilities**:
- Manage enabled strategies list
- Call `on_announcement` methods on strategy modules
- Handle strategy import errors gracefully

**Methods**:

| Method | Description |
|--------|-------------|
| `trigger_strategies(ticker, headline)` | Trigger all enabled strategies |

**Configuration**:
```bash
# Environment variables
TRIGGERS__ENABLED=true
TRIGGERS__STRATEGIES="asx_momentum,another_strategy"
```

### Scanner Service

**File**: `app/services/scanner_service.py:11`

**Refactored**: Orchestrates announcement scanning and publishes events.

**Responsibilities**:
- Run ASX announcement scanner
- Publish ScanStartedEvent
- Publish AnnouncementFoundEvent for each announcement
- Publish ScanCompletedEvent with results

**Methods**:

| Method | Description |
|--------|-------------|
| `scan()` | Run scanner and publish events |

## Event Handlers (NEW)

### DiscordHandler

**File**: `app/events/handlers/discord_handler.py`

Subscribes to AnnouncementFoundEvent and ScanCompletedEvent.
Uses NotificationService to send Discord notifications.

### StrategyHandler

**File**: `app/events/handlers/strategy_handler.py`

Subscribes to AnnouncementFoundEvent.
Uses StrategyTriggerService to trigger vn.py strategies.

### ImportHandler

**File**: `app/events/handlers/import_handler.py`

Subscribes to DownloadStartedEvent and ImportStartedEvent.
Executes CoolTrader download and CSV import logic.

## Scheduler Service

**File**: `app/scheduler/scheduler_service.py`

**Unified scheduler** that publishes events on cron schedule.

**Responsibilities**:
- Manage all cron schedules (scan, download, import)
- Publish ScanStartedEvent on schedule
- Publish DownloadStartedEvent on schedule
- Publish ImportStartedEvent on schedule

**Methods**:

| Method | Description |
|--------|-------------|
| `initialize()` | Register all scheduled jobs |
| `start()` | Start scheduler |
| `stop()` | Stop scheduler |
| `is_running()` | Check if scheduler is running |

## Event Types

### Announcement Events

- `ScanStartedEvent` - Scan initiated
- `AnnouncementFoundEvent` - Individual announcement discovered
- `ScanCompletedEvent` - Scan finished with results

### Data Import Events

- `DownloadStartedEvent` - Download initiated
- `DownloadCompletedEvent` - Download finished
- `ImportStartedEvent` - Import initiated
- `ImportCompletedEvent` - Import finished with stats

## Service Coordination

**Startup Sequence**:
1. EventBus starts
2. Services initialize (Gateway, Health, Notification, StrategyTrigger)
3. Event handlers register with EventBus
4. SchedulerService starts (publishes events on schedule)

**Runtime Flow**:
```
SchedulerService → EventBus.publish(ScanStartedEvent)
ScannerService → EventBus.publish(AnnouncementFoundEvent)
    ↓
EventBus
    ├→ DiscordHandler → NotificationService.send_discord_webhook()
    └→ StrategyHandler → StrategyTriggerService.trigger_strategies()
```

## Configuration

All services configured in `app/config.py` using Pydantic Settings (environment variables):

```bash
# IB Gateway
GATEWAY__HOST="ib-gateway"
GATEWAY__PORT=4004
GATEWAY__CLIENT_ID=1
GATEWAY__CONNECT_TIMEOUT=30
GATEWAY__AUTO_RECONNECT=true
GATEWAY__RECONNECT_INTERVAL=5
GATEWAY__MAX_RECONNECT_ATTEMPTS=10

# Health checks
HEALTH__ENABLED=true
HEALTH__INTERVAL_SECONDS=30
HEALTH__GATEWAY_TIMEOUT=5
HEALTH__UNHEALTHY_THRESHOLD=3

# ASX Scanner
SCANNERS__ENABLED=true
SCANNERS__ASX__SCAN_SCHEDULE="30 10 * * 1-5"

# Notifications
SCANNERS__NOTIFICATIONS__DISCORD__ENABLED=true

# Strategy triggers
SCANNERS__TRIGGERS__ENABLED=true
```

## Related Files

- Gateway: `app/gateway.py`, `app/gateway_scanner.py`
- Scanner: `app/scanner/`, `app/scanners/`
- Strategies: `app/strategies/`, `app/analysis/strategies/`
- Configuration: `app/config.py`
- EventBus: `app/events/bus.py`, `app/events/events.py`
- Handlers: `app/events/handlers/`
