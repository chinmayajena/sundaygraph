.PHONY: help build up down logs restart clean test format lint

help: ## Show this help message
	@echo 'Usage: make [target]'
	@echo ''
	@echo 'Available targets:'
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  %-15s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

build: ## Build Docker images
	docker-compose build

up: ## Start all services
	docker-compose up -d

down: ## Stop all services
	docker-compose down

logs: ## View logs
	docker-compose logs -f sundaygraph

restart: ## Restart all services
	docker-compose restart

clean: ## Remove containers and volumes
	docker-compose down -v
	docker system prune -f

test: ## Run tests
	uv run pytest tests/

format: ## Format code
	uv run black src/ tests/
	uv run ruff check --fix src/ tests/

lint: ## Lint code
	uv run ruff check src/ tests/
	uv run mypy src/

dev: ## Start development server
	uv run uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000

install: ## Install dependencies
	uv sync

