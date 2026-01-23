.PHONY: help install dev test lint type-check format clean build up down logs deploy

# Workflow:
# - Feature dev: Use create-worktree.sh (not this Makefile)
# - Production deploy: Use manual-deploy.sh in /opt/peaches
# - This Makefile: Local dev commands (format, lint, test, etc.)

help:  ## Show this help message
	@echo 'Usage: make [target]'
	@echo ''
	@echo 'Available targets:'
	@awk 'BEGIN {FS = ":.*##"}; { \
		if (/^@?([a-zA-Z_-]+):.*?##/ || /^[a-zA-Z_-]+:.*?##/) \
			printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2; \
		else if (/^@?([a-zA-Z_-]+):/ || /^[a-zA-Z_-]+:/) \
			print "  " $$1 }' $(MAKEFILE_LIST) | sort
	@echo ''

install:  ## Install dependencies with uv
	uv sync --all-extras

dev: install  ## Install development dependencies
	uv sync --all-extras --dev

test:  ## Run unit tests only (excludes integration)
	uv run pytest -m "not integration" --cov=app --cov-report=term --cov-report=html

test-integration:  ## Run integration tests
	uv run pytest -m integration --cov=app --cov-report=term --cov-report=html

test-all:  ## Run all tests (unit + integration)
	uv run pytest --cov=app --cov-report=term --cov-report=html

lint:  ## Run linting with ruff
	uv run ruff check app/

format:  ## Format code with ruff
	uv run ruff format app/

type-check:  ## Run type checking with mypy
	uv run mypy app/

check: lint type-check  ## Run all checks (lint + type-check)

build:  ## Build Docker image
	docker build -t $(REGISTRY_NAME):$(IMAGE_TAG) .

up:  ## Start Docker Compose
	docker compose up -d

down:  ## Stop Docker Compose
	docker compose down

logs:  ## Show Docker Compose logs
	docker compose logs -f

restart: down up  ## Restart Docker Compose

clean:  ## Clean up Docker resources
	docker compose down -v
	docker system prune -f

 deploy:  ## Deploy to production (uses manual-deploy.sh)
	@echo "Production deployment uses manual-deploy.sh"
	@echo "Use: cd /opt/peaches && ./manual-deploy.sh"

status:  ## Show status of all containers
	docker compose ps

health:  ## Check health status
	curl -s http://localhost:8080/health | jq

gateway-health:  ## Check IB Gateway status
	curl -s http://localhost:8080/health/gateway | jq

debug-vnc:  ## Enable VNC for debugging IBC
	@echo "Creating VNC password file..."
	@echo "vnc_password" > vnc_password.txt
	@echo ""
	@echo "Updating .env to enable VNC..."
	@echo "VNC_SERVER_PASSWORD_FILE=/run/secrets/vnc_password" >> .env
	@echo "VNC_PORT=5900" >> .env
	@echo ""
	@echo "Restarting ib-gateway with VNC enabled..."
	docker compose restart ib-gateway
	@echo ""
	@echo "VNC is now enabled."
	@echo "Connect VNC client to localhost:5900 with password: vnc_password"
	@echo ""
	@echo "To disable VNC, comment out VNC_SERVER_PASSWORD_FILE in .env and restart."

disable-vnc:  ## Disable VNC for production security
	@echo "Disabling VNC in .env..."
	@sed -i.bak '/^VNC_/s/^/#/' .env
	docker compose restart ib-gateway
	@echo "VNC disabled for production security."

all: format check test  ## Format, check, and run unit tests

.DEFAULT_GOAL := help
