# Phlow Development Makefile

.PHONY: help install test test-unit test-e2e lint format clean dev docs

help: ## Show this help message
	@echo "Phlow Development Commands:"
	@echo "=========================="
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

install: ## Install development dependencies
	uv pip install -e ".[dev,examples]"

test: test-unit ## Run all tests (unit tests only by default)

test-unit: ## Run unit tests with coverage
	uv run pytest tests/ -v --cov=src/phlow --cov-report=term-missing --cov-report=xml

test-e2e: ## Run end-to-end tests (requires Docker)
	cd examples/python-client && ./run_e2e_tests.sh

test-e2e-verbose: ## Run E2E tests with verbose output
	cd examples/python-client && ./run_e2e_tests.sh --verbose --slow

test-all: test-unit test-e2e ## Run both unit and E2E tests

lint: ## Run linting checks
	uv run ruff check src/ tests/ examples/
	uv run mypy src/

format: ## Format code
	uv run ruff format src/ tests/ examples/
	uv run ruff check src/ tests/ examples/ --fix

clean: ## Clean up build artifacts and caches
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info/
	rm -rf .pytest_cache/
	rm -rf .coverage
	rm -rf coverage.xml
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

dev: ## Start development environment
	cd examples/python-client && docker-compose up -d
	@echo "🚀 Development environment started!"
	@echo "   📊 Supabase Studio: http://localhost:54323"
	@echo "   🌐 Supabase API: http://localhost:54321"
	@echo "   🐍 Phlow Agent: http://localhost:8000"
	@echo "   📖 Agent Docs: http://localhost:8000/docs"

dev-stop: ## Stop development environment
	cd examples/python-client && docker-compose down

dev-logs: ## Show development environment logs
	cd examples/python-client && docker-compose logs -f

build: ## Build the package
	python -m build

publish-test: build ## Publish to Test PyPI
	twine upload --repository testpypi dist/*

publish: build ## Publish to PyPI
	twine upload dist/*

check: lint test-unit ## Run all checks (lint + unit tests)

ci: ## Simulate CI pipeline locally
	@echo "🏗️  Simulating CI pipeline..."
	$(MAKE) format
	$(MAKE) lint
	$(MAKE) test-unit
	@echo "✅ CI simulation complete!"

# Development shortcuts
up: dev ## Alias for dev
down: dev-stop ## Alias for dev-stop
logs: dev-logs ## Alias for dev-logs