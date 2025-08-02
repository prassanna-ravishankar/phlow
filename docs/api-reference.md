# API Reference

## Core Classes

### PhlowMiddleware

The main middleware class that handles authentication and A2A Protocol integration.

```python
from phlow import PhlowMiddleware, PhlowConfig

middleware = PhlowMiddleware(config)
```

#### Constructor Parameters

- `config: PhlowConfig` - Configuration object containing agent card, keys, and Supabase settings

#### Methods

##### `verify_jwt(token: str, agent_id: str) -> PhlowContext`
Verifies a JWT token and returns authentication context.

**Parameters:**
- `token` - JWT token to verify
- `agent_id` - ID of the agent making the request

**Returns:** `PhlowContext` object with agent information and Supabase client

**Raises:**
- `AuthenticationError` - Invalid or expired token
- `AgentNotFoundError` - Agent not found in registry

### PhlowConfig

Configuration object for Phlow middleware.

```python
config = PhlowConfig(
    agent_card=agent_card,
    private_key=private_key,
    supabase_url=supabase_url,
    supabase_anon_key=supabase_anon_key
)
```

#### Parameters

- `agent_card: AgentCard` - Agent information and capabilities
- `private_key: str` - RSA private key for signing JWTs
- `supabase_url: str` - Supabase project URL
- `supabase_anon_key: str` - Supabase anonymous key
- `enable_audit_logging: bool = True` - Enable authentication event logging
- `rate_limiting: Optional[RateLimitConfig] = None` - Rate limiting configuration

### PhlowContext

Authentication context object passed to authenticated endpoints.

#### Attributes

- `agent: AgentCard` - Information about the authenticated agent
- `supabase: Client` - Authenticated Supabase client
- `request_id: str` - Unique request identifier for logging
- `authenticated_at: datetime` - When authentication occurred

### AgentCard

Agent information and capabilities.

```python
agent_card = AgentCard(
    name="My Agent",
    description="Agent description",
    service_url="https://my-agent.com",
    skills=["chat", "analysis"],
    metadata={"agent_id": "my-agent-id", "public_key": "..."}
)
```

#### Parameters

- `name: str` - Human-readable agent name
- `description: str` - Agent description and purpose
- `service_url: str` - Agent's service endpoint URL
- `skills: List[str]` - List of agent capabilities
- `metadata: Dict[str, Any]` - Additional agent metadata including public key

## FastAPI Integration

### create_phlow_dependency

Creates a FastAPI dependency for authentication.

```python
from phlow.integrations.fastapi import create_phlow_dependency

auth_required = create_phlow_dependency(middleware)

@app.post("/api/endpoint")
async def endpoint(context: PhlowContext = Depends(auth_required)):
    return {"agent": context.agent.name}
```

### PhlowFastAPIMiddleware

ASGI middleware for automatic authentication.

```python
from phlow.integrations.fastapi import PhlowFastAPIMiddleware

app.add_middleware(PhlowFastAPIMiddleware, phlow_middleware=middleware)
```

## RBAC Classes

### RoleCredentialStore

Manages role credential storage and verification.

```python
from phlow.rbac import RoleCredentialStore

store = RoleCredentialStore(supabase_client)
```

#### Methods

##### `store_credential(agent_id: str, credential: dict) -> None`
Stores a verifiable credential for an agent.

##### `get_credentials(agent_id: str) -> List[dict]`
Retrieves all credentials for an agent.

##### `verify_role(agent_id: str, required_role: str) -> bool`
Verifies if an agent has the required role.

### RoleCredentialVerifier

Verifies W3C Verifiable Credentials.

```python
from phlow.rbac import RoleCredentialVerifier

verifier = RoleCredentialVerifier()
is_valid = await verifier.verify_credential(credential)
```

## Error Classes

### AuthenticationError
Raised when JWT verification fails.

### AgentNotFoundError
Raised when agent is not found in registry.

### RateLimitExceededError
Raised when rate limits are exceeded.

### CircuitBreakerOpenError
Raised when circuit breaker is open.

## Configuration Classes

### RateLimitConfig

Rate limiting configuration.

```python
from phlow.types import RateLimitConfig

rate_config = RateLimitConfig(
    requests_per_minute=60,
    burst_size=10,
    redis_url="redis://localhost:6379"
)
```

### MonitoringConfig

Monitoring and logging configuration.

```python
from phlow.monitoring import MonitoringConfig

monitoring = MonitoringConfig(
    enable_prometheus=True,
    enable_structured_logging=True,
    log_level="INFO"
)
```

## Utility Functions

### generate_rsa_keypair

Generates RSA key pair for agent authentication.

```python
from phlow.utils import generate_rsa_keypair

private_key, public_key = generate_rsa_keypair()
```

### verify_agent_signature

Verifies agent JWT signature.

```python
from phlow.utils import verify_agent_signature

is_valid = verify_agent_signature(token, public_key)
```

## Environment Variables

### Required

- `SUPABASE_URL` - Supabase project URL
- `SUPABASE_ANON_KEY` - Supabase anonymous key
- `AGENT_ID` - Unique agent identifier
- `AGENT_PRIVATE_KEY` - RSA private key for JWT signing

### Optional

- `PHLOW_ENABLE_AUDIT_LOGGING` - Enable audit logging (default: true)
- `PHLOW_RATE_LIMIT_REQUESTS` - Requests per minute (default: 60)
- `PHLOW_REDIS_URL` - Redis URL for distributed rate limiting
- `PHLOW_LOG_LEVEL` - Logging level (default: INFO)
- `PHLOW_ENABLE_PROMETHEUS` - Enable Prometheus metrics (default: false)

## Common Patterns

### Basic Authentication Setup

```python
from phlow import PhlowMiddleware, PhlowConfig, AgentCard

# Configure agent
config = PhlowConfig(
    agent_card=AgentCard(
        name="My Agent",
        description="My AI agent",
        service_url="https://my-agent.com",
        skills=["chat"],
        metadata={"agent_id": "my-agent", "public_key": public_key}
    ),
    private_key=private_key,
    supabase_url=os.environ["SUPABASE_URL"],
    supabase_anon_key=os.environ["SUPABASE_ANON_KEY"]
)

middleware = PhlowMiddleware(config)
```

### Error Handling

```python
from phlow.exceptions import AuthenticationError, AgentNotFoundError

try:
    context = middleware.verify_jwt(token, agent_id)
except AuthenticationError:
    return {"error": "Invalid token"}
except AgentNotFoundError:
    return {"error": "Agent not found"}
```

### Rate Limiting

```python
from phlow.types import RateLimitConfig

rate_config = RateLimitConfig(
    requests_per_minute=100,
    burst_size=20,
    redis_url="redis://localhost:6379"
)

config = PhlowConfig(
    # ... other config
    rate_limiting=rate_config
)
```
