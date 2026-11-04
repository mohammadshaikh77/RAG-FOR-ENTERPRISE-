.PHONY: up down build test lint format eval demo-data clean help

# Default target
all: help

help:
	@echo "Cite Platform - Command Shortcuts"
	@echo "=================================="
	@echo "  make up          - Start all containers via Docker Compose"
	@echo "  make down        - Stop and remove all containers"
	@echo "  make build       - Rebuild Docker images"
	@echo "  make test        - Run test suite via pytest"
	@echo "  make lint        - Run ruff linter and mypy type checks"
	@echo "  make format      - Automatically format code using ruff"
	@echo "  make demo-data   - Download & ingest sample pharma drug labels"
	@echo "  make eval        - Run the full evaluation harness and output report"
	@echo "  make clean       - Remove caches, temporary files, and volumes"

up:
	docker compose up -d

down:
	docker compose down

build:
	docker compose build

test:
	.venv/bin/pytest -v

lint:
	.venv/bin/ruff check .
	.venv/bin/mypy apps/api/src apps/worker/src

format:
	.venv/bin/ruff format .
	.venv/bin/ruff check --fix .

demo-data:
	.venv/bin/python scripts/fetch_demo_data.py

eval:
	.venv/bin/python eval/harness.py

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	find . -type d -name ".ruff_cache" -exec rm -rf {} +
	find . -type d -name ".mypy_cache" -exec rm -rf {} +
