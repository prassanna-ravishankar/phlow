# Developer Guide

Welcome to the Phlow developer guide. This section provides comprehensive technical documentation for developers working with or contributing to the Phlow Agent-to-Agent authentication framework.

## Quick Navigation

### 🏗️ Architecture & Design

- [**Project Architecture**](architecture.md) - System design and core principles
- [**Codebase Structure**](codebase-structure.md) - Monorepo organization and packages
- [**Database Schema**](database-schema.md) - Supabase tables and RLS policies

### 💻 Implementation Deep Dives

- [**JavaScript/TypeScript**](javascript-implementation.md) - Core middleware and JWT handling
- [**Python Implementation**](python-implementation.md) - Async APIs and framework integrations
- [**Authentication Flow**](authentication-flow.md) - End-to-end request processing

### 🔧 Development Workflow

- [**Local Development**](local-development.md) - Setup, building, and debugging
- [**Testing Strategy**](testing-strategy.md) - Unit, integration, and e2e testing
- [**Build & Deploy**](build-deploy.md) - Production deployment guide

### 📚 Reference

- [**API Reference**](api-reference.md) - Complete API documentation
- [**Configuration**](configuration.md) - Environment variables and settings
- [**Troubleshooting**](troubleshooting.md) - Common issues and solutions

## At a Glance

### Project Status

- **Mature Implementation**: Well beyond specification phase
- **Production Ready**: Rate limiting, audit logging, error handling
- **Multi-Language**: JavaScript/TypeScript and Python packages
- **A2A Compliant**: Full Agent-to-Agent protocol compatibility

### Quick Stats
```
📦 4 packages (auth-js, auth-python, cli, dev)
🧪 Integration test suite
📖 Comprehensive examples
🔒 JWT + Supabase security
⚡ Turborepo monorepo
```

### Key Technologies

- **TypeScript**: Core JS implementation with strict typing
- **Python**: Modern async/await with Pydantic validation
- **Supabase**: Backend registry and authentication
- **JWT**: RS256 signed tokens for security
- **Turborepo**: Monorepo orchestration and caching

## Contributing

Ready to contribute? Start with:

1. [**Local Development Setup**](local-development.md#setup)
2. [**Codebase Structure**](codebase-structure.md) overview
3. [**Testing Strategy**](testing-strategy.md) for your changes
4. [**Architecture**](architecture.md) principles

## Need Help?

- 🐛 **Found a bug?** Check [Troubleshooting](troubleshooting.md)
- 🤔 **Have questions?** See [Configuration](configuration.md)
- 🚀 **Ready to deploy?** Follow [Build & Deploy](build-deploy.md)

---

*This guide covers the technical implementation details. For user-focused documentation, see the [Getting Started Guide](../getting-started.md).*