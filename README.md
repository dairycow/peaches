# vn.py Trading Bot

Production-ready, headless trading bot for vn.py running in Docker with Interactive Brokers.

**Optimized for ASX trading** with Interactive Brokers Gateway.

## Features

 - **Headless Operation**: Runs without GUI using Xvfb virtual display
 - **Auto-Reconnect**: Handles IB Gateway disconnections gracefully
 - **CTA Strategies**: Supports vn.py CTA strategy framework
 - **Secure**: Docker network isolation, VNC opt-in for debugging only
 - **Health Checks**: Built-in health monitoring via HTTP endpoints
 - **Type-Safe**: Full type hints with Pydantic v2 validation
 - **Docker Compose**: Multi-container orchestration
 - **CI/CD**: Automated build, test, and deploy via GitHub Actions
 - **Modern Python**: Uses uv for fast dependency management
 - **SQLite Database**: Lightweight, persistent data storage

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│              Docker Network: trading                │
├─────────────────────────────────────────────────────────┤
│                                                   │
│  ┌──────────────────┐      ┌──────────────────┐    │
│  │   ib-gateway     │      │  trading-bot     │    │
│  │  (pre-built)     │      │   (custom)       │    │
│  ├──────────────────┤      ├──────────────────┤    │
│  │ • IB Gateway     │      │ • vn.py         │    │
│  │ • IBC 3.23.0   │◄────┤ • vnpy_ib       │    │
│  │ • Xvfb          │ TCP  │ • vnpy_cta      │    │
│  │ • socat         │      │ • Pydantic      │    │
│  │ • VNC (opt-in) │      │ • FastAPI       │    │
│  │ • Ports:        │      │ • SQLite DB     │    │
│  │   4003/4004    │      │                │    │
│  │   5900 (VNC)  │      │                │    │
│  └──────────────────┘      └──────────────────┘    │
└─────────────────────────────────────────────────────────┘

**Note**: VNC is disabled by default for security.
Enable only temporarily for debugging IBC login issues.
```

## Prerequisites

- Docker and Docker Compose
- Python 3.13 (for local development)
- Interactive Brokers account with API access
- GitHub account (for container registry)

### ASX Data Subscription

**Important**: Ensure your IBKR account has ASX data subscription active.

- Navigate to Account Management → Market Data Subscriptions
- Verify "Australian Securities (ASX)" or "Network A" is enabled
- Without this subscription, the bot will not receive market data for ASX stocks

Common ASX stocks to test:
- `BHP` - BHP Group
- `CBA` - Commonwealth Bank
- `ANZ` - ANZ Bank
- `TLS` - Telstra Corporation

## Quick Start

### 1. Clone and Configure

```bash
git clone https://github.com/dairycow/peaches.git
cd peaches

cp .env.example .env
```

### 2. Configure Secrets

Create IBKR password file:

```bash
echo "your_ibkr_password" > secrets/tws_password.txt
chmod 600 secrets/tws_password.txt
```

For optional VNC debugging:

```bash
echo "your_vnc_password" > secrets/vnc_password.txt
chmod 600 secrets/vnc_password.txt
```

### 3. Configure Environment

Edit `.env` with your credentials:

```env
TWS_USERID=your_ibkr_username
TRADING_MODE=paper  # or 'live' for real trading
```

### 4. Start with Docker Compose

```bash
docker compose up -d
```

### 4. Monitor Logs

```bash
# View all logs
docker compose logs -f

# View specific service
docker compose logs -f trading-bot
docker compose logs -f ib-gateway
```

### 5. Check Health

```bash
curl http://localhost:8080/health
```

## Development

### Local Development with uv

```bash
# Install uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# Create virtual environment
uv venv
source .venv/bin/activate

# Install dependencies
uv sync --all-extras

# Run tests
uv run pytest

# Run with type checking
uv run mypy app/

# Run linting
uv run ruff check app/
```

### Development Workflow

**Recommended Approach**: Use Docker for all development, including local development.

```bash
# Install dependencies locally (for type checking and linting)
uv sync --all-extras --dev

# Run type checking
uv run mypy app/

# Run linting
uv run ruff check app/

# Format code
uv run ruff format app/

# Run tests
uv run pytest
```

**Running Services**:

Always use Docker Compose for running services to maintain consistency between development and production:

```bash
# Start all services
docker compose up -d

# View logs
docker compose logs -f

# Stop services
docker compose down
```

**Why Docker for Development?**
- Consistent environment across dev and production
- No need to install IB Gateway locally
- Reproducible IBC behavior
- Easier debugging of networking issues

**Code Changes**:
When modifying strategy code or configuration:
1. Edit files locally
2. Restart trading-bot container: `docker compose restart trading-bot`
3. Check logs: `docker compose logs -f trading-bot`

**VNC for Debugging** (Optional):

If you need to debug IBC login issues on headless system:

```bash
# 1. Enable VNC in .env
# Uncomment: VNC_SERVER_PASSWORD_FILE=/run/secrets/vnc_password

# 2. Create VNC password file
echo "your_vnc_password" > vnc_password.txt

# 3. Restart ib-gateway
docker compose restart ib-gateway

# 4. Connect via VNC client
# Host: localhost, Port: 5900
```

**SSH Tunnel to Remote VPS** (Production Debugging):

```bash
# Forward VNC port from remote VPS
ssh -L 5900:localhost:5900 user@your-vps.com

# Now connect VNC client to localhost:5900
# This gives you GUI access to remote IB Gateway
```

## Configuration

### ASX Symbol Format

vn.py symbol format: `{SYMBOL}.{CURRENCY}-{TYPE}-{EXCHANGE}`

**ASX Examples:**
```yaml
# Direct ASX routing (recommended for ASX trading)
vt-symbol: "BHP-STK-ASX"    # BHP Group
vt-symbol: "CBA-STK-ASX"    # Commonwealth Bank
vt-symbol: "ANZ-STK-ASX"    # ANZ Bank
vt-symbol: "TLS-STK-ASX"    # Telstra

# SMART routing (use for multi-market strategies)
vt-symbol: "BHP-STK-SMART"   # BHP via SMART routing
```

**For Other Markets:**
```yaml
# US Stocks
vt-symbol: "AAPL-STK-SMART"   # Apple
vt-symbol: "SPY-STK-SMART"    # SPY ETF

# Forex
vt-symbol: "EURUSD-CASH-IDEALPRO"
```

### Settings File (config/settings.yaml)

```yaml
trading:
  max-position-size: 100
  risk-per-trade: 0.02
  stop-loss-pct: 0.02
  take-profit-pct: 0.04

strategy:
  name: "asx_momentum_strategy"
  vt-symbol: "BHP-STK-ASX"
  interval: "1m"
  parameters:
    fast_period: 10
    slow_period: 20
    rsi_period: 14
    rsi_overbought: 70
    rsi_oversold: 30

database:
  path: "/app/data/trading.db"
  backup-enabled: true
  backup-interval-hours: 24
```

### Environment Variables

| Variable | Description | Default |
|----------|-------------|----------|
| `TWS_USERID` | IBKR username | - |
| `TWS_PASSWORD` | IBKR password | - |
| `TRADING_MODE` | `live` or `paper` | `paper` |
| `IB_GATEWAY_HOST` | IB Gateway host | `ib-gateway` |
| `IB_GATEWAY_PORT` | IB Gateway port | `4004` |
| `LOG_LEVEL` | Log level | `INFO` |
| `TIME_ZONE` | Timezone for IB Gateway | `Etc/UTC` |
| `VNC_SERVER_PASSWORD_FILE` | Path to VNC password file (opt-in) | - |
| `VNC_PORT` | VNC port for debugging | `5900` |
| `AUTO_RESTART_TIME` | IB Gateway daily restart time (HH:MM AM/PM) | - |

**VNC Configuration (Optional)**:

VNC is **disabled by default** for security. Enable only for debugging IBC login issues:

```bash
# 1. Create password file
echo "your_password" > vnc_password.txt

# 2. Uncomment in .env
VNC_SERVER_PASSWORD_FILE=/run/secrets/vnc_password

# 3. Restart ib-gateway
docker compose restart ib-gateway

# 4. Connect VNC client
# Host: localhost, Port: 5900, Password: from vnc_password.txt
```

**Security Note**: Disable VNC in production. Only enable temporarily for debugging.

## API Endpoints

### Health Check

```bash
# Overall health
GET /health

# Gateway status
GET /health/gateway

# Readiness check
GET /health/ready

# Liveness check
GET /health/live
```

Example response:

```json
{
  "status": "healthy",
  "timestamp": "2026-01-16T12:00:00",
  "gateway_connected": true,
  "uptime_seconds": 3600.5,
  "version": "0.1.0"
}
```

### Documentation

- Swagger UI: http://localhost:8080/docs
- ReDoc: http://localhost:8080/redoc

## Creating Strategies

### Base Strategy Template

```python
from app.strategies import BaseCtaStrategy

class MyStrategy(BaseCtaStrategy):
    def _setup_parameters(self) -> None:
        self.fast_period: int = 10
        self.slow_period: int = 20

    def on_init(self) -> None:
        self.bg = self.bg = self.bg = self.bg = BarGenerator(
            self.on_bar,
            window=self.fast_period,
            on_window_bar=self.on_fast_bar,
        )
        # Initialize indicators, etc.

    def on_start(self) -> None:
        # Subscribe to data
        # Send initial orders
        pass

    def on_stop(self) -> None:
        # Cleanup logic
        pass

    def on_tick(self, tick: TickData) -> None:
        # Process tick data
        pass

    def on_bar(self, bar: BarData) -> None:
        # Process bar data
        pass
```

## Deployment

### Automatic Deployment

Push to `main` branch triggers automatic deployment:

1. **Build**: Docker image built and pushed to GHCR
2. **Test**: All tests run
3. **Lint**: Code quality checks
4. **Deploy**: Deployed via SSH to VPS

### Manual Deployment

```bash
# Build image
docker build -t ghcr.io/your-username/vnpy-trading-bot:latest .

# Push to registry
docker push ghcr.io/your-username/vnpy-trading-bot:latest

# Deploy to VPS
ssh user@your-vps.com
cd /opt/vnpy-trading-bot
git pull origin main
docker compose pull
docker compose down
docker compose up -d
```

## Monitoring

### Logs

```bash
# Real-time logs
docker compose logs -f trading-bot

# Last 100 lines
docker compose logs --tail=100 trading-bot
```

### Health Monitoring

```bash
# Check health status
watch -n 5 curl -s http://localhost:8080/health | jq
```

### Metrics

Key metrics to monitor:
- Connection uptime
- Order execution latency
- Strategy performance
- Error rates
- Resource usage (CPU, memory)

## Security

### Best Practices

1. **Use Docker Secrets**: Store sensitive data in Docker secrets
2. **Never Commit Secrets**: `.env` is in `.gitignore`
3. **Docker Network**: Keep IB Gateway on isolated network
4. **SSH Tunnel**: For remote access, use SSH tunneling
5. **Regular Updates**: Keep images and dependencies updated

### Docker Secrets Example

```yaml
secrets:
  tws_password:
    file: ./secrets/tws_password.txt
  vnc_password:
    file: ./secrets/vnc_password.txt
```

## Troubleshooting

### IBC Login Issues (Critical)

IBC (Interactive Brokers Controller) can fail if IBKR changes their login screen. Since you're running headless, you can't see the login prompt.

**Symptoms:**
- IB Gateway container starts but never becomes healthy
- Bot fails to connect to Gateway
- Logs show IBC waiting indefinitely

**Solutions:**

1. **Enable VNC for Visual Debugging**:
   ```bash
   # Enable VNC in .env
   VNC_SERVER_PASSWORD_FILE=/run/secrets/vnc_password
   VNC_PORT=5900

   # Create password file
   echo "your_vnc_password" > vnc_password.txt

   # Restart ib-gateway
   docker compose restart ib-gateway

   # Connect VNC client to localhost:5900
   # You can now see IBC attempting login
   ```

2. **Check IB Gateway Logs for IBC Errors**:
   ```bash
   docker compose logs ib-gateway | grep -i "error\|fail\|login"
   ```

3. **Verify IBKR Credentials**:
   - Ensure TWS_USERID is correct
   - Verify password (2FA is handled separately by IBC)

4. **Check IBKR Account Status**:
   - Ensure your account is active
   - Verify API permissions are enabled

5. **Temporary Workaround**:
   - If IBC is consistently failing, manually log in via TWS app once
   - Save credentials (IBKR allows saving login session)
   - Restart IBC container

**Prevention:**
- Set `AUTO_RESTART_TIME` to daily restart time (e.g., 04:00 AM)
- This refreshes the session before 2FA timeout issues occur

### IB Gateway Won't Connect

1. Check IB Gateway logs:
   ```bash
   docker compose logs ib-gateway
   ```

2. Verify IB Gateway is healthy:
   ```bash
   docker ps
   ```

3. Check network connectivity:
    ```bash
    docker exec ib-gateway timeout 2 bash -c '</dev/tcp/localhost/4003' && echo "Port 4003 is open" || echo "Port 4003 is closed"
    docker exec ib-gateway timeout 2 bash -c '</dev/tcp/localhost/4004' && echo "Port 4004 is open" || echo "Port 4004 is closed"
    ```

### Strategy Not Starting

1. Check trading bot logs:
   ```bash
   docker compose logs trading-bot
   ```

2. Verify gateway connection:
   ```bash
   curl http://localhost:8080/health/gateway
   ```

3. Check strategy initialization:
   ```bash
   curl http://localhost:8080/docs
   ```

### High CPU/Memory Usage

1. Check resource usage:
   ```bash
   docker stats
   ```

2. Adjust Java heap size:
   ```env
   JAVA_HEAP_SIZE=1024
   ```

3. Reduce logging level:
   ```env
   LOG_LEVEL=WARNING
   ```

### ASX-Specific Issues

1. **No Market Data for ASX Stocks**:
   - Check IBKR account has "Australian Securities" subscription
   - Navigate to Account Management → Market Data Subscriptions
   - Verify ASX data is active

2. **Symbol Format Errors**:
   ```bash
   # Correct ASX format
   vt-symbol: "BHP-STK-ASX"

   # Common mistakes (will fail)
   vt-symbol: "BHP-ASX"        # Missing type
   vt-symbol: "BHP.STK-ASX"      # Wrong separator
   vt-symbol: "BHP-STK-NYSE"    # Wrong exchange
   ```

3. **Order Rejection - No Market Data**:
   - ASX symbols require `STK` type
   - Verify exchange is `ASX` or `SMART`
   - Check subscription is active for the specific instrument

4. **Trading Hours Considerations**:
   ```python
   # ASX trading hours (AEST)
   # Market open: 10:00 AM
   # Market close: 4:00 PM
   # Pre-open: 7:00 AM - 10:00 AM
   # Post-close: 4:10 PM - 4:30 PM
   ```

5. **ASX-Specific Risk Rules**:
   - Ensure position sizing respects ASX contract multipliers
   - ASX stocks trade in minimum lot sizes (typically 1)
   - Check IBKR for symbol-specific minimums

## Production Deployment Checklist

Before deploying to production VPS:

### Configuration
- [ ] TRADING_MODE set to `live` (only after thorough paper trading)
- [ ] IBKR credentials tested and working
- [ ] ASX data subscription active and verified
- [ ] Symbol formats validated (e.g., `BHP-STK-ASX`)
- [ ] Risk parameters reviewed and approved
- [ ] AUTO_RESTART_TIME configured to avoid 2FA issues

### Security
- [ ] VNC disabled in .env (VNC_PASSWORD_FILE commented out)
- [ ] Docker secrets configured for sensitive data
- [ ] SSH keys properly set up for VPS access
- [ ] GitHub secrets configured (VPS_HOST, VPS_USER, VPS_SSH_KEY)
- [ ] Firewall rules allow only necessary ports (SSH only)
- [ ] Log rotation configured to prevent disk exhaustion

### Monitoring
- [ ] Health check endpoint accessible
- [ ] Log aggregation configured (or plans for it)
- [ ] Alerting configured for failures
- [ ] Resource monitoring set up (CPU, memory, disk)
- [ ] Database backup strategy in place

### Testing
- [ ] Strategy tested extensively in paper mode
- [ ] No active orders before deployment
- [ ] IB Gateway auto-restart tested
- [ ] Network connectivity verified
- [ ] Rollback procedure documented

### VPS Setup
- [ ] Docker and Docker Compose installed
- [ ] Sufficient disk space (recommended 20GB+)
- [ ] Timezone configured correctly
- [ ] NTP time synchronization enabled
- [ ] Docker daemon configured to start on boot

### Post-Deployment
- [ ] Monitor logs for first 24 hours
- [ ] Verify IB Gateway health status
- [ ] Check strategy is executing orders correctly
- [ ] Confirm no errors in health checks
- [ ] Validate trade executions match expectations

## Historical Data Management

### Data Pipeline

The bot downloads and imports ASX historical data automatically:

1. **10:00 AM AEST** - Download yesterday's CSV from CoolTrader
2. **10:05 AM AEST** - Import all CSVs to vn.py database

### Manual Operations

**Trigger CoolTrader download:**
```bash
curl -X POST http://localhost:8080/import/download/trigger
```

**Trigger CSV import:**
```bash
curl -X POST http://localhost:8080/import/import/trigger
```

**Start scheduler:**
```bash
curl -X POST http://localhost:8080/import/schedule/start
```

**Check scheduler status:**
```bash
curl http://localhost:8080/import/schedule/status
```

### Database Queries

**View database stats:**
```bash
curl http://localhost:8080/import/database/stats
```

**View data overview:**
```bash
curl http://localhost:8080/import/database/overview
```

### Strategy Integration

Strategies can access historical data via vn.py database:

```python
from app.database import get_database_manager
from vnpy.trader.constant import Interval
from datetime import datetime

db_manager = get_database_manager()
bars = db_manager.load_bars(
    symbol="BHP",
    exchange=Exchange.LOCAL,
    interval=Interval.DAILY,
    start=datetime(2020, 1, 1),
    end=datetime(2024, 1, 1),
)

for bar in bars:
    print(f"{bar.datetime}: {bar.close_price}")
```

### CSV File Format

Place CSV files in `data/csv/` directory:

```
SYMBOL,DD/MM/YYYY,OPEN,HIGH,LOW,CLOSE,VOLUME
BHP,14/01/2026,30.7,30.96,30.3,30.3,613098
```

File naming: `YYYYMMDD.csv` (e.g., `20260117.csv`)

## Testing

```bash
# Run all tests
uv run pytest

# Run with coverage
uv run pytest --cov=app --cov-report=html

# Run specific test
uv run pytest tests/test_gateway.py
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests: `uv run pytest`
5. Run linting: `uv run ruff check app/`
6. Run type checking: `uv run mypy app/`
7. Submit a pull request

## License

MIT License - see LICENSE file for details

## Support

- Documentation: https://www.vnpy.com/docs
- IB Gateway Docker: https://github.com/gnzsnz/ib-gateway-docker
- Issues: https://github.com/your-username/vnpy-trading-bot/issues

## Disclaimer

This software is for educational purposes only. Use at your own risk. Trading in financial markets involves substantial risk of loss and is not suitable for every investor.
