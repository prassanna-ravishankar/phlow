# Codebase Structure

This guide explains the organization of the Phlow monorepo, package architecture, and how the different components work together.

## Monorepo Overview

Phlow uses **Turborepo** for efficient monorepo management with intelligent caching and parallel execution.

```
phlow/
├── packages/                 # Core libraries and tools
│   ├── phlow-auth-js/       # JavaScript/TypeScript authentication library
│   ├── phlow-auth-python/   # Python authentication library
│   ├── phlow-cli/           # Command-line development tools
│   └── phlow-dev/           # Local development utilities
├── examples/                # Working examples and demos
│   ├── basic-agent/         # Simple Express.js agent
│   ├── multi-agent-network/ # Complex agent coordination
│   └── python-client/       # FastAPI example with Docker
├── tests/                   # Cross-package integration tests
├── docs/                    # Documentation (this guide!)
├── tools/                   # Build and deployment scripts
└── turbo.json              # Turborepo pipeline configuration
```

## Build System

### Turborepo Configuration

**Pipeline Definition** (`turbo.json`):
```json
{
  "pipeline": {
    "build": {
      "dependsOn": ["^build"],
      "outputs": ["dist/**", "build/**"]
    },
    "dev": {
      "cache": false,
      "persistent": true
    },
    "test": {
      "dependsOn": ["build"]
    },
    "lint": {}
  }
}
```

**Key Features**:
- **Dependency-aware builds**: Packages build in correct order
- **Intelligent caching**: Skip unchanged packages
- **Parallel execution**: Build multiple packages simultaneously
- **Workspace linking**: Automatic cross-package dependencies

### Common Commands

```bash
# Build all packages
npm run build

# Development mode (watch for changes)
npm run dev

# Run tests across all packages
npm run test

# Lint all code
npm run lint

# Clean all build artifacts
npm run clean
```

## Package Details

### phlow-auth-js

**Location**: `/packages/phlow-auth-js/`
**Purpose**: Core JavaScript/TypeScript authentication middleware

```
src/
├── index.ts              # Main exports
├── middleware.ts         # PhlowMiddleware class
├── jwt.ts               # JWT operations
├── types.ts             # TypeScript interfaces
├── errors.ts            # Error classes
├── supabase-helpers.ts  # Database utilities
└── utils.ts             # Helper functions
```

**Key Files**:

- **`middleware.ts`**: Core `PhlowMiddleware` class with `authenticate()` and `wellKnownHandler()` methods
- **`jwt.ts`**: JWT generation, verification, and validation utilities
- **`types.ts`**: Complete TypeScript type definitions for AgentCard, PhlowConfig, etc.
- **`supabase-helpers.ts`**: Agent card CRUD operations and RLS policy generation

**Build Configuration**:
```json
{
  "main": "dist/index.js",
  "module": "dist/index.mjs", 
  "types": "dist/index.d.ts",
  "exports": {
    ".": {
      "import": "./dist/index.mjs",
      "require": "./dist/index.js",
      "types": "./dist/index.d.ts"
    }
  }
}
```

**Dependencies**:
- `@supabase/supabase-js`: Database client
- `jsonwebtoken`: JWT operations
- `crypto`: Cryptographic functions

### phlow-auth-python

**Location**: `/packages/phlow-auth-python/`
**Purpose**: Python authentication library with async/sync support

```
src/phlow_auth/
├── __init__.py           # Package exports
├── middleware.py         # Core PhlowMiddleware class
├── jwt_utils.py         # JWT operations
├── types.py             # Pydantic models and types
├── exceptions.py        # Exception hierarchy
├── supabase_helpers.py  # Database utilities
├── audit.py             # Audit logging
├── rate_limiter.py      # Rate limiting
└── integrations/
    ├── __init__.py
    └── fastapi.py       # FastAPI integration
```

**Key Features**:

- **Dual Async/Sync APIs**: Every operation has both async and sync versions
- **Pydantic Validation**: Runtime data validation and serialization
- **Framework Integrations**: FastAPI dependency injection pattern
- **Advanced Features**: Rate limiting, audit logging, RLS policy generation

**Build Configuration** (`pyproject.toml`):
```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
dependencies = [
    "PyJWT[crypto]>=2.8.0",
    "supabase>=2.0.0", 
    "cryptography>=41.0.0",
    "pydantic>=2.0.0"
]
```

**Optional Dependencies**:
```toml
[project.optional-dependencies]
fastapi = ["fastapi>=0.100.0"]
flask = ["flask>=2.0.0"]
django = ["django>=4.0.0"]
dev = ["pytest", "mypy", "black", "isort"]
```

### phlow-cli

**Location**: `/packages/phlow-cli/`
**Purpose**: Command-line tools for development and testing

```
src/
├── index.ts             # CLI entry point
├── commands/
│   ├── init.ts         # Project initialization
│   ├── generate-keys.ts # RSA key generation
│   ├── test-token.ts   # Token testing
│   └── dev-start.ts    # Development server
├── utils/
│   ├── config.ts       # Configuration management
│   ├── templates.ts    # Project templates
│   └── logging.ts      # CLI logging
└── types.ts            # CLI-specific types
```

**Available Commands**:
```bash
# Initialize new project
phlow init my-agent

# Generate RSA key pair
phlow generate-keys

# Test authentication with another agent
phlow test-token --target agent-id

# Start development environment
phlow dev-start
```

**Key Features**:
- **Interactive project setup** with Inquirer.js
- **RSA key generation** with secure defaults
- **Token testing utilities** for debugging
- **Development server** with hot reload

### phlow-dev

**Location**: `/packages/phlow-dev/`
**Purpose**: Local development utilities and mock services

```
src/
├── index.ts            # Main exports
├── mock-server.ts      # Mock Supabase server
├── test-agents.ts      # Pre-configured test agents
├── scenarios.ts        # Test scenarios
└── utils/
    ├── network.ts      # Network utilities
    └── database.ts     # Mock database
```

**Features**:
- **Mock Supabase server** for offline development
- **Pre-configured test agents** with known keys
- **Test scenarios** for common authentication flows
- **Network simulation** for testing edge cases

## Examples Directory

### basic-agent

**Location**: `/examples/basic-agent/`
**Purpose**: Simple Express.js agent with Phlow authentication

```
├── index.js            # Main server
├── package.json        # Dependencies
├── .env.example       # Environment template
├── README.md          # Setup instructions
├── test.js            # Integration test
└── test-unit.js       # Unit tests
```

**Key Features**:
- Basic Express.js setup
- Phlow middleware integration
- Protected and public routes
- Agent card discovery endpoint

### multi-agent-network

**Location**: `/examples/multi-agent-network/`
**Purpose**: Complex scenario with multiple coordinated agents

```
├── coordinator.js      # Main orchestration logic
├── agents/
│   ├── auth-agent.js  # Authentication service
│   ├── compute-agent.js # Computation service
│   └── data-agent.js   # Data processing service
├── test-network.js     # End-to-end network test
└── package.json
```

**Features**:
- Service discovery patterns
- Inter-agent communication
- Permission-based routing
- Distributed task processing

### python-client

**Location**: `/examples/python-client/`
**Purpose**: FastAPI implementation with Docker support

```
├── main.py             # FastAPI application
├── client_helper.py    # Agent client utilities
├── test_client.py      # pytest test suite
├── requirements.txt    # Python dependencies
├── Dockerfile          # Container setup
├── docker-compose.yml  # Multi-service setup
└── README.md
```

**Features**:
- FastAPI dependency injection
- Docker containerization
- Pytest test suite
- Multi-service coordination

## Integration Tests

**Location**: `/tests/`
**Purpose**: Cross-package integration and end-to-end testing

```
tests/
├── integration/
│   ├── js-python-interop.test.ts    # Cross-language tests
│   ├── multi-agent-auth.test.ts     # Multi-agent scenarios
│   └── performance.test.ts          # Performance benchmarks
├── e2e/
│   ├── full-workflow.test.ts        # Complete user workflows
│   └── edge-cases.test.ts           # Error conditions
└── utils/
    ├── test-agents.ts               # Shared test agents
    └── assertions.ts                # Custom assertions
```

## Configuration Files

### Root Configuration

**`package.json`** (workspace root):
```json
{
  "workspaces": ["packages/*", "examples/*"],
  "scripts": {
    "build": "turbo run build",
    "dev": "turbo run dev",
    "test": "turbo run test",
    "lint": "turbo run lint"
  }
}
```

**`tsconfig.json`** (shared TypeScript config):
```json
{
  "compilerOptions": {
    "strict": true,
    "target": "ES2020",
    "module": "commonjs",
    "declaration": true,
    "paths": {
      "@phlow/*": ["packages/*/src"]
    }
  }
}
```

### Package-Specific Configuration

**TypeScript packages** use:
- `tsup` for fast building with TypeScript support
- `jest` for testing framework
- `eslint` + `prettier` for code quality

**Python packages** use:
- `hatchling` for modern Python packaging
- `pytest` for testing
- `mypy` for type checking
- `black` + `isort` for code formatting

## Development Patterns

### Cross-Package Dependencies

**Internal dependencies** are handled automatically:
```json
{
  "dependencies": {
    "phlow-auth-js": "workspace:*"
  }
}
```

**Type sharing** across packages:
```typescript
// packages/phlow-cli/src/types.ts
import type { AgentCard } from 'phlow-auth-js'
```

### Code Generation

**Shared types** between JS and Python:
- TypeScript interfaces define the contract
- Python Pydantic models mirror the types
- Automated validation ensures compatibility

### Testing Strategy

**Package-level tests**:
- Unit tests for individual functions
- Integration tests for package features

**Cross-package tests**:
- JS ↔ Python interoperability
- CLI integration with libraries
- Example application testing

## Build Outputs

### JavaScript/TypeScript

**Distribution formats**:
- **CommonJS**: `dist/index.js` for Node.js
- **ESM**: `dist/index.mjs` for modern environments
- **Types**: `dist/index.d.ts` for TypeScript

### Python

**Distribution formats**:
- **Wheel**: `.whl` for pip installation
- **Source**: `.tar.gz` for source installation
- **Types**: `py.typed` marker for type checking

## Maintenance

### Dependency Management

**JavaScript**: Uses npm workspaces with shared lockfile
**Python**: Uses pip-tools for reproducible environments

### Version Management

**Synchronized versioning** across all packages using Changesets:
```bash
npm run changeset        # Create changeset
npm run version         # Update versions  
npm run release         # Publish packages
```

### Code Quality

**Automated checks**:
- TypeScript compilation
- ESLint + Prettier (JS)
- mypy + black (Python)
- Unit and integration tests
- Documentation generation

---

This structure provides a scalable foundation for the Phlow ecosystem while maintaining clear separation of concerns and efficient development workflows.