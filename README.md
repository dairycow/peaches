# Peaches Trading Bot

Trading bot for vn.py running in Docker with Interactive Brokers.

**Optimized for ASX trading** with IB Gateway.

## Quick Start

```bash
git clone https://github.com/dairycow/peaches.git
cd peaches
cp .env.example .env

# Set IBKR credentials in .env
echo "your_password" > secrets/tws_password.txt
chmod 600 secrets/tws_password.txt

# Start
docker compose up -d

# Check health
curl http://localhost:8080/api/v1/health
```

**Important**: Ensure your IBKR account has ASX data subscription active (Account Management → Market Data Subscriptions).

## Development

```bash
# Install uv and dependencies
curl -LsSf https://astral.sh/uv/install.sh | sh
uv venv && source .venv/bin/activate
uv sync --all-extras

# Run all checks
make check

# Start services (always use Docker for consistency)
docker compose up -d
docker compose logs -f

# Worktree development (keeps main clean)
./create-worktree.sh feature/new-feature
# Work in ~/peaches-feature-new-feature/
# When done: ./merge-worktree.sh feature/new-feature
```

**Style Guidelines**:
- Python 3.13+
- 100 char line length
- Self-documenting code (no comments)
- Docstrings for public APIs

## Configuration

**ASX Symbol Format**: `{SYMBOL}-{TYPE}-{EXCHANGE}`
```yaml
# Direct ASX routing (recommended)
vt-symbol: "BHP-STK-ASX"    # BHP Group
vt-symbol: "CBA-STK-ASX"    # Commonwealth Bank

# SMART routing (multi-market)
vt-symbol: "BHP-STK-SMART"
```

**Key Environment Variables** (.env):
- `TWS_USERID` - IBKR username
- `TRADING_MODE` - `paper` or `live`
- `IB_GATEWAY_PORT` - Default `4004`
- `LOG_LEVEL` - `INFO`
- `AUTO_RESTART_TIME` - Daily IB Gateway restart time (HH:MM AM/PM)

**VNC Debugging** (optional, security risk):
```bash
# Uncomment in .env: VNC_SERVER_PASSWORD_FILE=/run/secrets/vnc_password
echo "password" > secrets/vnc_password.txt
docker compose restart ib-gateway
# Connect VNC client to localhost:5900
```

## API Endpoints

**Health**: `GET /api/v1/health`, `GET /api/v1/health/gateway`, `GET /api/v1/health/ready`, `GET /api/v1/health/live`

**Data Import**:
- `POST /api/v1/import/download/trigger` - Trigger CoolTrader CSV download
- `POST /api/v1/import/download/date` - Download specific date
- `POST /api/v1/import/import/trigger` - Trigger CSV import to database
- `GET /api/v1/import/database/stats` - Database statistics
- `GET /api/v1/import/database/overview` - Symbol data overview
- `POST /api/v1/import/schedule/start` - Start scheduled imports
- `POST /api/v1/import/schedule/stop` - Stop scheduled imports
- `GET /api/v1/import/schedule/status` - Scheduler status

**Scanners**:
- `POST /api/v1/scanners/trigger` - Manual announcement scan
- `GET /api/v1/scanners/status` - Scanner status

**Announcement Gap Strategy**:
- `POST /api/v1/announcement-gap/scan` - Scan for gap breakout candidates
- `POST /api/v1/announcement-gap/sample-opening-ranges` - Scan with opening range sampling

**Interactive Docs**: http://localhost:8080/docs

## Deployment

```bash
cd /opt/peaches
./manual-deploy.sh
```

Deployment pulls from `origin/main`, validates secrets, rebuilds images, and restarts containers.

**Automatic**: Push to `main` triggers CI/CD pipeline (build → test → lint → deploy to VPS).

## Monitoring

```bash
# Logs
docker compose logs -f peaches-bot
docker compose logs --tail=100 peaches-bot

# Health status
watch -n 5 curl -s http://localhost:8080/api/v1/health | jq
```

## Historical Data

Automatic pipeline (AEST):
- 10:00 AM - Download CSV from CoolTrader
- 10:05 AM - Import to vn.py database

**Manual**:
```bash
curl -X POST http://localhost:8080/api/v1/import/import/trigger
curl http://localhost:8080/api/v1/import/database/stats
```

CSV format: `symbol,date,open,high,low,close,volume` (date: `%d/%m/%Y`)

## Troubleshooting

**IBC Login Issues**:
- Enable VNC (see above) to visually debug
- Check logs: `docker compose logs ib-gateway | grep -i "error\|fail\|login"`
- Set `AUTO_RESTART_TIME` to daily restart (e.g., 04:00 AM)

**No ASX Market Data**:
- Verify IBKR account has "Australian Securities" subscription
- Check symbol format: `BHP-STK-ASX` (not `BHP-ASX` or `BHP.STK-ASX`)

**Connection Issues**:
```bash
docker compose logs ib-gateway
docker compose logs peaches-bot
docker exec ib-gateway timeout 2 bash -c '</dev/tcp/localhost/4004'
```

**High Resource Usage**:
- Check: `docker stats`
- Adjust: `JAVA_HEAP_SIZE=1024` in .env
- Reduce logging: `LOG_LEVEL=WARNING`

## Support

- vn.py Documentation: https://www.vnpy.com/docs
- IB Gateway Docker: https://github.com/gnzsnz/ib-gateway-docker
- AGENTS.md - Detailed development guidelines
