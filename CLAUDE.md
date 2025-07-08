# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Phlow is an Agent-to-Agent (A2A) authentication framework that integrates with Supabase. It aims to become the de facto standard for authentication between AI agents, making agent auth as simple as adding middleware in a few lines of code.

## Project Status

Currently in the **specification phase** - the codebase contains detailed plans but no implementation yet. The README.md contains the comprehensive specification for the project.

## Planned Architecture

The project will use a middleware pattern:
```
Client Agent → Phlow Middleware → Remote Agent + Supabase
```

Key components:
- JWT-based authentication
- Supabase integration for backend services
- Row Level Security (RLS) helpers
- Rate limiting and audit logging

## Development Commands

Since the project is not yet implemented, here are the planned development workflows:

### Initial Setup (Future)
```bash
# Install dependencies
npm install  # for JS packages
pip install -r requirements.txt  # for Python packages

# Start local development environment
phlow dev-start  # Will start local Supabase instance
```

### Testing (Future)
```bash
# Run integration tests
npm test  # or yarn test

# Run specific test file
npm test -- path/to/test.spec.js

# Run e2e tests
npm run test:e2e
```

### Building (Future)
```bash
# Build JavaScript package
npm run build

# Lint code
npm run lint

# Type checking
npm run typecheck
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

## Implementation Phases

1. **Phase 1 (MVP)**: Core JavaScript middleware with Supabase integration
2. **Phase 2 (Ecosystem)**: Python library, CLI tools, local dev environment
3. **Phase 3 (Scale)**: Advanced features, community building

## Key Technical Decisions

- **Primary Language**: TypeScript/JavaScript for initial implementation
- **Authentication**: JWT-based with Supabase backend
- **Package Names**: `phlow-auth` (npm), `phlow_auth` (pip)
- **CLI Tool**: `phlow` command for development and testing

## A2A SDK Integration

Phlow extends the A2A Protocol SDKs with Supabase integration. Here are the SDK locations and versions:

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
- `A2ACardResolver` - For resolving agent cards from network

**Python (a2a-sdk):**
- `a2a.client.A2AClient` - For sending messages to other agents
- `a2a.types.AgentCard` - Agent card type definition
- `a2a.types.Message` - Message type definition
- `a2a.types.Task` - Task type definition

## Important Context

When implementing features, ensure they align with the project's core principles:
- Simplicity: Authentication should be achievable in just a few lines of code
- Developer Experience: Provide excellent local testing capabilities
- Security: Follow JWT best practices and leverage Supabase's security features
- Extensibility: Design for future protocol support beyond JWT