#!/usr/bin/env bash

set -e

DEPLOY_DIR="/opt/peaches"
cd "${DEPLOY_DIR}"

echo "=== Deployment started ==="
echo "Branch: main"
echo "Commit: $(git rev-parse HEAD)"

echo "=== Pulling latest code ==="
git fetch origin
git reset --hard origin/main

echo "=== Loading environment variables ==="
if [ -f .env ]; then
  set -a
  source .env
  set +a
fi

echo "=== Validating required files ==="
for secret in ./secrets/tws_password.txt ./secrets/vnc_password.txt; do
  if [ ! -f "$secret" ]; then
    echo "❌ Required secret file missing: $secret"
    exit 1
  fi
done

echo "=== Validating required environment variables ==="
required_vars=("TWS_USERID" "TRADING_MODE" "COOLTRADER_USERNAME")
for var in "${required_vars[@]}"; do
  if [ -z "${!var}" ]; then
    echo "❌ Required variable missing: $var"
    exit 1
  fi
done

echo "=== Rebuilding and restarting containers ==="
docker compose down --remove-orphans || true
docker compose build
docker compose up -d

echo "=== Checking jq installation ==="
if ! command -v jq &> /dev/null; then
  sudo apt-get update && sudo apt-get install -y jq
fi

echo "=== Waiting for all services to be healthy (max 300s) ==="
timeout 300 bash -c '
  until [ "$(docker compose ps --format json | jq -r "select(.Health == \"healthy\") | .Service" | wc -l)" -eq "$(docker compose ps --format json | jq ". | length")" ]; do
    sleep 5
  done
' || {
  echo "❌ Health check failed!"
  echo "=== Showing recent logs ==="
  docker compose logs --tail=50
  exit 1
}

docker compose ps

echo "=== Deployment completed successfully ==="
