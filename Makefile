SHELL := /bin/sh
.DEFAULT_GOAL := help

UV ?= uv
COMPOSE ?= docker compose
SERVICE ?= waterbot

.PHONY: help setup setup-hardware config check-config sync-config sync-config-dry-run run \
	compile lint format format-check test check \
	docker-config docker-build docker-up docker-down docker-stop docker-start docker-restart \
	docker-logs docker-ps docker-shell docker-exec

help: ## Show available commands
	@awk 'BEGIN {FS = ":.*## "; printf "Usage: make <target>\n\nTargets:\n"} /^[a-zA-Z0-9_-]+:.*## / {printf "  %-18s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

setup: ## Install locked backend and development dependencies
	$(UV) sync --locked --dev

setup-hardware: ## Install the optional ESP tooling dependency group
	$(UV) sync --locked --dev --group hardware

config: ## Create config.yaml from the example if it does not exist
	@test -e config.yaml || cp example.config.yaml config.yaml
	@echo "config.yaml is ready; replace every placeholder before running Waterbot."

check-config:
	@test -f config.yaml || { echo "config.yaml is missing; run 'make config' first." >&2; exit 1; }

sync-config: check-config ## Generate private MicroPython constants from config.yaml
	$(UV) run python -m backend.sync_config

sync-config-dry-run: check-config ## Validate IoT configuration without writing secrets
	$(UV) run python -m backend.sync_config --dry-run

run: check-config ## Run the backend locally (live Telegram and HTTP connections)
	PYTHONPATH=. $(UV) run python backend/backend_main.py

compile: ## Compile-check CPython backend sources
	$(UV) run python -m compileall -q backend tests

lint: ## Run Ruff diagnostics
	$(UV) run ruff check .

format: ## Format automated test sources with Ruff
	$(UV) run ruff format tests

format-check: ## Check automated test formatting without changing files
	$(UV) run ruff format --check tests

test: ## Run the local unit test suite
	$(UV) run pytest

check: format-check lint test compile ## Run all safe local quality checks

docker-config: check-config ## Validate the rendered Compose configuration
	$(COMPOSE) config --quiet

docker-build: docker-config ## Build the backend container image
	$(COMPOSE) build

docker-up: docker-config ## Build and start the backend in the background
	$(COMPOSE) up --build --detach

docker-down: ## Stop and remove containers; preserve the database volume
	$(COMPOSE) down

docker-stop: ## Stop running containers without removing them
	$(COMPOSE) stop

docker-start: ## Start previously created containers
	$(COMPOSE) start

docker-restart: ## Restart the backend container
	$(COMPOSE) restart $(SERVICE)

docker-logs: ## Follow backend container logs
	$(COMPOSE) logs --follow --tail=200 $(SERVICE)

docker-ps: ## Show Compose container status
	$(COMPOSE) ps

docker-shell: docker-config ## Open a disposable shell in the image
	$(COMPOSE) run --rm --no-deps $(SERVICE) sh

docker-exec: ## Open a shell in the running backend container
	$(COMPOSE) exec $(SERVICE) sh
