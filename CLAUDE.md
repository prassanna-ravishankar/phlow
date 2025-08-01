# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Phlow is a Python authentication middleware library for AI agents that integrates with the A2A (Agent-to-Agent) Protocol and Supabase. The project uses modern Python tooling with UV package manager, Ruff for linting/formatting, and ty for type checking.

## Essential Commands

### Development Setup
```bash
uv sync --dev              # Install all dependencies including dev tools
```

### Testing
```bash
uv run task test           # Run full test suite with coverage
uv run task test-unit      # Run unit tests only (excludes E2E)
uv run task test-e2e       # Run E2E tests (requires Docker)
```

### Code Quality - ALWAYS RUN BEFORE COMPLETING TASKS
```bash
uv run task lint           # Run Ruff linting with auto-fix
uv run task format         # Format code with Ruff
uv run task type-check     # Type checking with ty
uv run task quality        # Run all quality checks (lint + format + type-check)
```

### Build and Release
```bash
uv run task build          # Build distributable packages
uv run task clean          # Clean build artifacts
```

## Architecture Overview

### Core Structure
- `src/phlow/` - Main library code
  - `middleware.py` - Core PhlowMiddleware class that handles JWT verification and A2A integration
  - `types.py` - Pydantic models for type safety (AgentCard, TaskRequest, TaskResponse, etc.)
  - `supabase_helpers.py` - Supabase integration for agent registry and audit logging
  - `integrations/` - Framework-specific integrations (currently FastAPI, planned Flask/Django)

### Key Patterns
1. **Middleware Pattern**: The `PhlowMiddleware` class integrates with web frameworks to handle authentication
2. **A2A Protocol Compliance**: Implements agent discovery at `/.well-known/agent.json` and task execution at `/tasks/send`
3. **Type-Safe Design**: Extensive use of Pydantic models and type hints throughout
4. **Dependency Injection**: Framework integrations use dependency injection for clean authentication handling

### Testing Strategy
- Unit tests in `tests/test_basic.py` for core functionality
- E2E tests use Docker to spin up full environments with Supabase
- Test markers: `slow`, `integration`, `e2e` (E2E tests skipped in CI)

## Important Notes

- The project requires Python 3.10+ and uses UV as the package manager
- E2E tests require Docker (automatically detects Docker Desktop or Rancher Desktop)
- Always run `uv run task quality` before completing any code changes
- The project is migrating from MyPy to ty for faster type checking
- Supabase integration requires proper environment variables (see `docs/configuration.md`)
- All task commands are defined in `pyproject.toml` under `[tool.taskipy.tasks]`
