# Phlow - Agent-to-Agent Authentication Framework

<div class="hero-section" markdown>
<img src="phlow-logo.png" alt="Phlow Logo" class="hero-logo">

JWT-based authentication for AI agent networks using Supabase.

[Get Started](getting-started.md){ .md-button .md-button--primary }
[View on GitHub](https://github.com/prassanna-ravishankar/phlow){ .md-button }
</div>

## Features

<div class="grid cards" markdown>

-   :material-security: **JWT Authentication**

    ---

    RS256-signed JWT tokens for secure agent-to-agent communication with Supabase as the registry.

-   :simple-javascript: **JavaScript & Python**

    ---

    Libraries for JavaScript/TypeScript and Python. Additional language support planned.

-   :simple-supabase: **Supabase Integration**

    ---

    Uses Supabase for agent registry and public key storage. Other auth backends planned.

-   :material-console: **CLI Tools**

    ---

    Command-line tools for project setup, key generation, and testing.

-   :material-cog: **Middleware**

    ---

    Express.js and FastAPI middleware for easy integration into existing projects.

-   :material-book: **Documentation**

    ---

    Working examples and comprehensive API documentation.

</div>

## Quick Start

=== "Installation"

    ```bash
    # Install Phlow CLI
    npm install -g phlow-cli
    ```

=== "Initialize Project"

    ```bash
    # Initialize new project
    phlow init my-agent
    ```

=== "Development"

    ```bash
    # Start development server
    phlow dev-start
    
    # Test authentication
    phlow test-token --target my-agent
    ```

## Current State & A2A Compatibility

!!! info "A2A Protocol Inspiration"

    Phlow is inspired by the [A2A Protocol specification](https://a2aproject.github.io/A2A/latest/specification/) and aims to provide A2A-compatible authentication as a foundation for agent networks.

**Current Features:**
- ✅ JWT-based authentication (compatible with A2A security schemes)
- ✅ Agent registry via Supabase (similar to A2A AgentCards)
- ✅ JavaScript/TypeScript and Python libraries
- ✅ Express.js and FastAPI middleware
- ✅ CLI tools for development and testing

**A2A Compatibility Roadmap:**
- 🔄 **AgentCard standard**: Implement A2A-compatible AgentCard format
- 🔄 **JSON-RPC 2.0**: Add JSON-RPC support alongside REST APIs  
- 🔄 **Well-known endpoints**: Support `/.well-known/agent.json` discovery
- 🔄 **Task management**: Add A2A task delegation and state management
- 🔄 **Streaming support**: Implement Server-Sent Events for real-time updates
- 🔄 **Multiple auth schemes**: Support OAuth 2.0, OpenID Connect, API keys
- 🔄 **Enhanced security**: TLS 1.3+ requirements and credential management

## How It Works

```mermaid
graph TB
    A[Agent A] -->|1. Generate JWT| A
    A -->|2. Send Request + JWT| B[Agent B]
    B -->|3. Lookup Public Key| S[Supabase Registry]
    S -->|4. Return Public Key| B
    B -->|5. Verify JWT Signature| B
    B -->|6. Process Request| B
    B -->|7. Send Response| A
```

**Authentication Flow:**

1. **Agent A** creates a JWT token signed with its private key
2. **Agent A** sends a request to **Agent B** with the JWT in the Authorization header  
3. **Agent B** looks up **Agent A's** public key from the Supabase registry
4. **Agent B** verifies the JWT signature using **Agent A's** public key
5. If valid, **Agent B** processes the request and sends a response

## Documentation

- [Getting Started Guide](getting-started.md) - Set up your first agent
- [API Reference](api-reference.md) - Complete API documentation  
- [Examples](examples/basic-agent.md) - Working code examples