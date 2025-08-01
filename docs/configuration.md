# Configuration

Configure Phlow for your A2A agent.

## Required Environment Variables

```bash
# Supabase (required)
SUPABASE_URL="https://your-project.supabase.co"
SUPABASE_ANON_KEY="your-anon-key"

# Authentication (required)
PRIVATE_KEY="-----BEGIN RSA PRIVATE KEY-----..."
PUBLIC_KEY="-----BEGIN PUBLIC KEY-----..."

# AI Integration (optional)
GEMINI_API_KEY="your-gemini-api-key"
```

## Agent Configuration

```python
from phlow import AgentCard, PhlowConfig

config = PhlowConfig(
    agent_card=AgentCard(
        name="My Agent",
        description="A2A compliant AI agent",
        service_url="https://my-agent.com",
        skills=["chat", "analysis"],
        metadata={
            "agent_id": "unique-agent-id",
            "public_key": os.getenv("PUBLIC_KEY")
        }
    ),
    private_key=os.getenv("PRIVATE_KEY"),
    supabase_url=os.getenv("SUPABASE_URL"),
    supabase_anon_key=os.getenv("SUPABASE_ANON_KEY")
)
```

## FastAPI Integration

```python
from phlow.integrations.fastapi import FastAPIPhlowAuth

auth = FastAPIPhlowAuth(config)

@app.post("/protected")
@auth.require_agent_auth
async def protected_endpoint(request: Request):
    agent = request.state.agent
    return {"agent": agent.name}
```

## Optional Features

### Audit Logging
```python
config = PhlowConfig(
    # ... other config
    enable_audit=True  # Logs auth events to Supabase
)
```

### Rate Limiting
```python
from phlow import RateLimiter

rate_limiter = RateLimiter(
    max_requests=100,
    window_seconds=60
)
```

## Development Commands

```bash
# Install dependencies
uv sync --dev

# Run tests
uv run task test-unit        # Unit tests
uv run task test-e2e         # E2E tests (requires Docker)

# Code quality
uv run task lint             # Lint and fix
uv run task format           # Format code
uv run task type-check       # Type checking

# Development server
uv run task dev-example      # Run example agent
```

## RSA Key Generation

```bash
# Generate private key
openssl genrsa -out private.pem 2048

# Extract public key
openssl rsa -in private.pem -pubout -out public.pem

# Set environment variables
export PRIVATE_KEY="$(cat private.pem)"
export PUBLIC_KEY="$(cat public.pem)"
```

## Docker Setup

For E2E testing:

```bash
# Docker Desktop
docker --version

# Rancher Desktop (auto-detected)
ls ~/.rd/docker.sock

# Test Docker access
uv run task test-e2e
```
