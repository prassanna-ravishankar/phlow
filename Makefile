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
	@echo "🐳 Detecting Docker setup..."
	@if [ -S "$$HOME/.rd/docker.sock" ]; then \
		echo "✅ Rancher Desktop detected"; \
		DOCKER_HOST=unix://$$HOME/.rd/docker.sock uv run pytest tests/test_e2e*.py -v -s; \
	else \
		echo "✅ Using default Docker setup"; \
		uv run pytest tests/test_e2e*.py -v -s; \
	fi

test-e2e-single: ## Run single-agent E2E tests
	@echo "🐳 Running single-agent E2E tests..."
	@if [ -S "$$HOME/.rd/docker.sock" ]; then \
		DOCKER_HOST=unix://$$HOME/.rd/docker.sock uv run pytest tests/test_e2e.py -v -s; \
	else \
		uv run pytest tests/test_e2e.py -v -s; \
	fi

test-e2e-multi: ## Run multi-agent E2E tests
	@echo "🐳 Running multi-agent E2E tests..."
	@if [ -S "$$HOME/.rd/docker.sock" ]; then \
		DOCKER_HOST=unix://$$HOME/.rd/docker.sock uv run pytest tests/test_e2e_multi_agent.py -v -s; \
	else \
		uv run pytest tests/test_e2e_multi_agent.py -v -s; \
	fi

test-e2e-verbose: ## Run E2E tests with verbose output
	@if [ -S "$$HOME/.rd/docker.sock" ]; then \
		DOCKER_HOST=unix://$$HOME/.rd/docker.sock uv run pytest tests/test_e2e.py -v -s --tb=long; \
	else \
		uv run pytest tests/test_e2e.py -v -s --tb=long; \
	fi

test-all: test-unit test-e2e ## Run both unit and E2E tests

lint: ## Run linting checks
	uv run ruff check src/ tests/
	uv run mypy src/

format: ## Format code
	uv run ruff format src/ tests/
	uv run ruff check src/ tests/ --fix

clean: ## Clean up build artifacts and caches
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info/
	rm -rf .pytest_cache/
	rm -rf .coverage
	rm -rf coverage.xml
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

dev: ## Start development environment (run example)
	cd docs/examples/simple && python main.py
	@echo "🚀 Development agent started!"
	@echo "   🐍 Phlow Agent: http://localhost:8000"
	@echo "   📖 Agent Docs: http://localhost:8000/docs"

dev-example: ## Install and run the simple example
	cd docs/examples/simple && pip install -r requirements.txt && python main.py

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