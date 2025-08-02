# Examples

Phlow provides several example implementations to help you get started quickly. All examples are maintained in the main repository and include complete documentation and working code.

## Available Examples

### 🚀 [Simple Agent](https://github.com/prassanna-ravishankar/phlow/tree/main/examples/simple)

A minimal A2A Protocol compliant agent demonstrating:
- Basic Phlow middleware setup
- A2A Protocol endpoints (`/.well-known/agent.json`, `/tasks/send`)
- AI integration example with Gemini
- Error handling and logging

**Files:**
- `README.md` - Complete setup and usage guide
- `main.py` - FastAPI application with Phlow integration
- `requirements.txt` - Dependencies

**Quick start:**
```bash
cd examples/simple
pip install -r requirements.txt
python main.py
```

---

### 🔄 [Multi-Agent Communication](https://github.com/prassanna-ravishankar/phlow/tree/main/examples/multi-agent)

Demonstrates agent-to-agent communication using the A2A Protocol:
- Multiple agents discovering each other
- Secure JWT-based authentication between agents
- Task delegation and response handling
- Network topology and agent registry

**Files:**
- `README.md` - Multi-agent setup guide
- `main.py` - Multi-agent orchestration example
- `requirements.txt` - Dependencies

**Use case:** Building agent networks where agents can discover and communicate with each other securely.

---

### 🔐 [RBAC Agent](https://github.com/prassanna-ravishankar/phlow/tree/main/examples/rbac_agent)

Advanced example showing Role-Based Access Control with Verifiable Credentials:
- W3C Verifiable Credentials for role management
- Cryptographic verification of role credentials
- Role-based endpoint protection
- Credential storage and management
- DID (Decentralized Identifier) integration

**Files:**
- `README.md` - Comprehensive RBAC setup guide
- `main.py` - FastAPI app with RBAC protection
- `requirements.txt` - Dependencies with RBAC extras

**Features demonstrated:**
- `@require_role("admin")` decorators
- Verifiable credential exchange
- Role credential storage and verification
- Integration with Supabase for credential registry

---

## Getting Started

### 1. Choose Your Example

- **New to Phlow?** Start with the [Simple Agent](https://github.com/prassanna-ravishankar/phlow/tree/main/examples/simple)
- **Building agent networks?** Use [Multi-Agent Communication](https://github.com/prassanna-ravishankar/phlow/tree/main/examples/multi-agent)
- **Need role-based security?** Check out the [RBAC Agent](https://github.com/prassanna-ravishankar/phlow/tree/main/examples/rbac_agent)

### 2. Clone and Setup

```bash
git clone https://github.com/prassanna-ravishankar/phlow.git
cd phlow/examples/[chosen-example]
pip install -r requirements.txt
```

### 3. Configure Environment

Each example includes detailed environment setup in its README. Common requirements:
- Supabase project and credentials
- RSA key pair for JWT signing
- Optional: AI provider API keys

### 4. Run and Test

```bash
python main.py
```

Then test the A2A Protocol endpoints:
```bash
# Agent discovery
curl http://localhost:8000/.well-known/agent.json

# Test basic connectivity
curl http://localhost:8000/health
```

## Development Workflow

Each example follows the same structure for consistency:

```
examples/[name]/
├── README.md          # Complete documentation
├── main.py           # Main application code
├── requirements.txt  # Python dependencies
└── .env.example      # Environment variables template
```

## Integration Patterns

All examples demonstrate key Phlow patterns:

### Authentication Middleware
```python
from phlow import PhlowMiddleware, PhlowConfig
from phlow.integrations.fastapi import create_phlow_dependency

config = PhlowConfig(...)
middleware = PhlowMiddleware(config)
auth_required = create_phlow_dependency(middleware)
```

### A2A Protocol Compliance
```python
@app.get("/.well-known/agent.json")
def agent_card():
    return config.agent_card.model_dump()

@app.post("/tasks/send")
async def send_task(context: PhlowContext = Depends(auth_required)):
    # Handle A2A tasks
    pass
```

### Error Handling
```python
try:
    context = middleware.verify_jwt(token, agent_id)
except AuthenticationError:
    raise HTTPException(401, "Authentication failed")
```

## Testing Examples

### Unit Tests
```bash
# From project root
uv run task test-unit
```

### E2E Tests
```bash
# Requires Docker
uv run task test-e2e
```

### Manual Testing
Each example README includes curl commands for manual testing.

## Production Deployment

For production deployment of any example:

1. **Security**: Follow the [Production Deployment Guide](production-deployment.md)
2. **Monitoring**: Enable [monitoring and logging](monitoring.md)
3. **Scaling**: Configure [rate limiting and circuit breakers](rate-limiting.md)

## Contributing Examples

We welcome new examples! When contributing:

1. Follow the standard structure (README, main.py, requirements.txt)
2. Include comprehensive documentation
3. Add E2E tests if applicable
4. Update this overview page

See our [contribution guide](https://github.com/prassanna-ravishankar/phlow/blob/main/CONTRIBUTING.md) for details.

## Support

- **Documentation**: Each example has detailed setup instructions
- **Issues**: Report problems on [GitHub Issues](https://github.com/prassanna-ravishankar/phlow/issues)
- **Discussions**: Ask questions in [GitHub Discussions](https://github.com/prassanna-ravishankar/phlow/discussions)

---

**Next Steps:**
- [Installation Guide](installation.md) - Set up your environment
- [Quick Start](quickstart.md) - Build your first agent
- [API Reference](api-reference.md) - Complete API documentation
