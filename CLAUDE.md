# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Phlow provides authentication and storage layers for the A2A (Agent-to-Agent) Protocol. While A2A handles agent communication, Phlow adds the missing pieces for production use: JWT-based authentication middleware, persistent agent registry in Supabase, and Row Level Security (RLS) policies.

## Project Status

Currently in **active development** - core packages are implemented with A2A SDK integration. The project provides production-ready authentication and storage extensions for A2A agents.

## Value Proposition

**What A2A Provides:**
- Agent-to-agent communication protocol
- Message passing and task management
- Agent card format and discovery
- JSON-RPC communication

**What A2A Doesn't Provide:**
- Authentication middleware
- Agent verification/auth flows
- Persistent agent storage
- Access control mechanisms

**What Phlow Adds:**
- 🔐 **Authentication Middleware** - JWT-based auth for Express/FastAPI
- 🗃️ **Persistent Agent Registry** - Store/retrieve agent cards in Supabase
- 🛡️ **Row Level Security (RLS)** - Generate Supabase RLS policies for agent access

## Planned Architecture

The project provides three core components:
```
A2A Communication + Phlow Auth + Supabase Storage = Complete Agent Infrastructure
```

Focused scope:
- **Authentication Middleware** - JWT verification for agent requests
- **Agent Registry** - Persistent storage of agent cards in Supabase
- **RLS Policies** - Generate access control policies for agent data

## Development Commands

### JavaScript Package
```bash
# Install dependencies
npm install

# Build JavaScript package
npm run build -w phlow-auth

# Lint code (ALWAYS run before committing)
npm run lint -w phlow-auth

# Type checking (ALWAYS run before committing)
npm run typecheck -w phlow-auth

# Run tests (ALWAYS run before committing)
npm run test -w phlow-auth
```

### Python Package
```bash
# Install dependencies
uv install

# Run tests (ALWAYS run before committing)
uv run pytest tests/

# Run specific test file
uv run pytest tests/test_basic.py -v

# Lint code (ALWAYS run before committing)
uv run ruff check src/

# Format code (ALWAYS run before committing)
uv run ruff format src/
```

## Project Structure (Planned)

```
phlow/
├── packages/
│   ├── phlow-auth-js/      # JavaScript/TypeScript library
│   ├── phlow-auth-python/  # Python library  
│   ├── phlow-cli/          # CLI tools
│   └── phlow-dev/          # Local development suite
├── examples/               # Example implementations
├── docs/                   # Documentation
└── tests/                  # Integration and e2e tests
```

## Implementation Status

- ✅ **JavaScript Package** - Core middleware with A2A integration
- ✅ **Python Package** - Core middleware with A2A integration
- ✅ **Supabase Integration** - Agent registry and RLS helpers
- ✅ **Authentication** - JWT-based middleware for both platforms
- 🚧 **CLI Tools** - Development utilities (in progress)
- 🚧 **Documentation** - API reference and guides (in progress)

## Key Technical Decisions

- **Focused Scope**: Authentication + Storage layer for A2A Protocol
- **A2A Integration**: Extends official A2A SDKs rather than reimplementing
- **Authentication**: JWT-based with Supabase backend
- **Package Names**: `phlow-auth` (npm), `phlow_auth` (pip)
- **Platform Support**: JavaScript/TypeScript and Python

## A2A SDK Integration

Phlow extends the A2A Protocol SDKs with authentication and storage capabilities. Here are the SDK locations and versions:

### JavaScript SDK
- **Package**: `a2a-js`
- **Version**: `0.2.0` (latest)
- **Repository**: https://github.com/a2aproject/a2a-js
- **NPM**: https://www.npmjs.com/package/a2a-js
- **Documentation**: https://a2aproject.github.io/A2A/latest/sdk/javascript/

### Python SDK
- **Package**: `a2a-sdk`
- **Version**: `0.2.11` (latest)
- **Repository**: https://github.com/a2aproject/a2a-python
- **Documentation**: https://a2aproject.github.io/A2A/latest/sdk/python/

### Key Classes to Use

**JavaScript (a2a-js):**
- `A2AClient` - For sending messages to other agents
- `A2AServer` - For handling incoming A2A tasks
- Used for communication while Phlow handles auth/storage

**Python (a2a-sdk):**
- `a2a.client.A2AClient` - For sending messages to other agents
- `a2a.types.AgentCard` - Agent card type definition
- `a2a.types.Message` - Message type definition
- `a2a.types.Task` - Task type definition
- Used for communication while Phlow handles auth/storage

## Important Context

When implementing features, ensure they align with the project's core principles:
- **Focused Scope**: Only authentication, agent registry, and RLS - no reimplementation of A2A communication
- **Simplicity**: Authentication should be achievable in just a few lines of code
- **A2A Compatibility**: Always extend A2A SDK, never replace it
- **Security**: Follow JWT best practices and leverage Supabase's security features
- **Production Ready**: Focus on features needed for production agent deployments

## Feature Parity Requirement

**CRITICAL**: Always maintain feature parity between JavaScript and Python packages.

- **When adding a new feature**: Implement it in BOTH JavaScript and Python packages
- **When fixing a bug**: Apply the fix to BOTH packages if applicable
- **When updating APIs**: Update BOTH packages to maintain consistent interfaces
- **When writing tests**: Write equivalent tests for BOTH packages

### Feature Parity Checklist:
- [ ] New method exists in both `PhlowMiddleware` classes
- [ ] Method signatures are equivalent (accounting for language differences)
- [ ] Both packages export the same types/interfaces
- [ ] Error handling is consistent between packages
- [ ] Documentation is updated for both packages
- [ ] Tests cover the feature in both packages

## Quality Assurance

**ALWAYS run these commands before committing:**

### JavaScript
```bash
npm run lint -w phlow-auth
npm run typecheck -w phlow-auth
npm run test -w phlow-auth
```

### Python
```bash
uv run pytest tests/
uv run ruff check src/
uv run ruff format src/
```

**If any command fails, fix the issues before committing.**