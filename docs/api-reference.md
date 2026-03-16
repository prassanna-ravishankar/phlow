# API Reference

## Quick Start (No Supabase)

```python
from phlow import PhlowAuth

auth = PhlowAuth(private_key="your-secret")
token = auth.create_token(agent_id="my-agent", name="My Agent")
claims = auth.verify(token)
```

## Full Setup (With Supabase)

```python
from phlow import PhlowMiddleware, PhlowConfig, AgentCard

config = PhlowConfig(
    agent_card=AgentCard(
        name="My Agent",
        service_url="https://my-agent.com",
        skills=["chat"],
        metadata={"agent_id": "my-agent-id"}
    ),
    private_key="your-secret",
    supabase_url="https://your-project.supabase.co",
    supabase_anon_key="your-anon-key"
)

middleware = PhlowMiddleware(config)
```

---

## Core Classes

### PhlowAuth

Lightweight JWT authentication. No Supabase required.

```python
from phlow import PhlowAuth

auth = PhlowAuth(
    private_key="secret",       # Required. HS256 string or RS256 PEM key
    public_key=None,            # Required for RS256 verification
    algorithm=None,             # Auto-detected from key format ("HS256" or "RS256")
    token_expiry_hours=1.0,     # Default token lifetime
)
```

#### Methods

| Method | Description |
|--------|-------------|
| `create_token(agent_id, name, permissions, extra_claims, expiry_hours)` | Create a signed JWT |
| `create_token_for_agent(agent_card)` | Create a JWT from an AgentCard |
| `verify(token)` | Verify a JWT and return claims |

### PhlowMiddleware

Full middleware with Supabase integration, RBAC, rate limiting, and circuit breakers.

```python
from phlow import PhlowMiddleware, PhlowConfig

middleware = PhlowMiddleware(config)
```

#### Methods

| Method | Description |
|--------|-------------|
| `verify_token(token)` | Verify JWT, return `PhlowContext` |
| `generate_token(agent_card)` | Generate JWT for an agent |
| `authenticate_with_role(token, role)` | Verify JWT + RBAC role (async) |
| `get_a2a_client()` | Get the A2A client instance |
| `get_supabase_client()` | Get the Supabase client |
| `authenticate()` | Get a generic auth middleware function |
| `aclose()` | Close resources (async) |

Supports async context manager: `async with PhlowMiddleware(config) as mw:`

### PhlowConfig

```python
from phlow import PhlowConfig

config = PhlowConfig(
    supabase_url="...",                    # Required
    supabase_anon_key="...",               # Required
    agent_card=AgentCard(...),             # Required
    private_key="...",                     # Required
    public_key=None,                       # For RS256
    enable_audit_log=False,                # Log auth events to Supabase
    rate_limit_configs=RateLimitConfigs(), # Rate limiting settings
)
```

### AgentCard

```python
from phlow import AgentCard

card = AgentCard(
    name="My Agent",              # Required
    description="...",            # Agent description
    service_url="...",            # Agent's URL
    skills=["chat", "search"],    # Capabilities
    metadata={"agent_id": "..."}  # Must include agent_id for JWT sub claim
)
```

### PhlowContext

Returned by `verify_token()` and FastAPI auth dependencies.

| Attribute | Type | Description |
|-----------|------|-------------|
| `agent` | `AgentCard` | The middleware's agent card |
| `token` | `str` | The raw JWT token |
| `claims` | `dict` | Decoded JWT claims |
| `supabase` | `Client` | Supabase client instance |
| `a2a_client` | `A2AClient` | A2A Protocol client |
| `verified_roles` | `list[str]` | RBAC-verified roles |

---

## FastAPI Integration

### FastAPIPhlowAuth

```python
from fastapi import Depends, FastAPI
from phlow import PhlowMiddleware, PhlowContext
from phlow.integrations.fastapi import FastAPIPhlowAuth

app = FastAPI()
middleware = PhlowMiddleware(config)
auth = FastAPIPhlowAuth(middleware)

# Auto-register /.well-known/agent.json
auth.setup_agent_card_route(app)

# Create auth dependency
auth_required = auth.create_auth_dependency()

@app.post("/api/endpoint")
async def endpoint(ctx: PhlowContext = Depends(auth_required)):
    return {"agent": ctx.agent.name, "sub": ctx.claims["sub"]}
```

#### Methods

| Method | Description |
|--------|-------------|
| `create_auth_dependency(required_permissions=None)` | Create FastAPI `Depends()` for JWT auth |
| `create_role_auth_dependency(required_role)` | Create FastAPI `Depends()` for RBAC auth |
| `setup_agent_card_route(app)` | Register `/.well-known/agent.json` endpoint |

### Convenience Functions

```python
from phlow.integrations.fastapi import create_phlow_dependency, create_phlow_role_dependency

auth_dep = create_phlow_dependency(middleware, required_permissions=["read"])
role_dep = create_phlow_role_dependency(middleware, required_role="admin")
```

---

## Token Utilities

```python
from phlow import generate_token, verify_token, decode_token

# Generate (standalone, without middleware)
token = generate_token(agent_card, private_key)

# Verify (checks signature + expiry)
claims = verify_token(token, public_key)

# Decode (no verification — for debugging)
claims = decode_token(token)
```

## CLI

```bash
# Generate a test token
phlow generate-token --key SECRET --agent-id my-agent --name "My Agent"

# Inspect a token (no key needed)
phlow decode-token TOKEN

# Verify a token
phlow verify-token TOKEN --key SECRET
```

---

## Exceptions

| Exception | HTTP Status | Description |
|-----------|-------------|-------------|
| `PhlowError` | 500 | Base exception |
| `AuthenticationError` | 401 | Token verification failed |
| `AuthorizationError` | 403 | Insufficient permissions |
| `ConfigurationError` | 500 | Invalid configuration |
| `TokenError` | 401 | Token operation failed |
| `RateLimitError` | 429 | Rate limit exceeded |
| `CircuitBreakerError` | 503 | Circuit breaker open |

All exceptions include `.message`, `.code`, and `.status_code` attributes.

---

## Rate Limiting

```python
from phlow.rate_limiter import RateLimiter

limiter = RateLimiter(max_requests=100, window_ms=60_000)

if limiter.is_allowed("user-id"):
    # process request
    pass

# Or raise on limit exceeded
limiter.check_and_raise("user-id")
```

For distributed rate limiting with Redis:

```python
from phlow.distributed_rate_limiter import DistributedRateLimiter

limiter = DistributedRateLimiter(
    max_requests=100,
    window_ms=60_000,
    redis_url="redis://localhost:6379",  # Falls back to in-memory if unavailable
)
```

---

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `SUPABASE_URL` | For PhlowMiddleware | Supabase project URL |
| `SUPABASE_ANON_KEY` | For PhlowMiddleware | Supabase anonymous key |
| `REDIS_URL` | No | Redis URL for distributed rate limiting |
| `PHLOW_KEY_STORE_TYPE` | No | Key storage backend: `environment`, `encrypted_file`, `vault`, `aws` |
