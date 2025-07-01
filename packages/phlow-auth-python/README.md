# Phlow Auth Python

Agent-to-Agent (A2A) authentication library for Python with Supabase integration.

## Installation

```bash
pip install phlow-auth
```

### Optional Dependencies

For framework integrations:

```bash
# FastAPI
pip install phlow-auth[fastapi]

# Flask
pip install phlow-auth[flask]

# Django
pip install phlow-auth[django]

# Development tools
pip install phlow-auth[dev]
```

## Quick Start

### Basic Usage

```python
from phlow_auth import PhlowMiddleware, PhlowConfig, AgentCard

# Configure your agent
config = PhlowConfig(
    supabase_url="https://your-project.supabase.co",
    supabase_anon_key="your-anon-key",
    agent_card=AgentCard(
        agent_id="my-agent",
        name="My Agent",
        permissions=["read:data", "write:data"],
        public_key="-----BEGIN PUBLIC KEY-----\n...",
    ),
    private_key="-----BEGIN RSA PRIVATE KEY-----\n...",
    enable_audit=True,
)

# Initialize middleware
phlow = PhlowMiddleware(config)
```

### FastAPI Integration

```python
from fastapi import FastAPI, Depends
from phlow_auth.integrations.fastapi import create_phlow_dependency

app = FastAPI()

# Create auth dependency
auth_required = create_phlow_dependency(phlow)
admin_required = create_phlow_dependency(phlow, required_permissions=["admin:users"])

@app.get("/protected")
async def protected_endpoint(context = Depends(auth_required)):
    return {
        "message": "Access granted!",
        "agent": context.agent.name,
        "permissions": context.claims.permissions
    }

@app.get("/admin")
async def admin_endpoint(context = Depends(admin_required)):
    return {"message": "Admin access granted!"}
```

### Manual Authentication

```python
from phlow_auth import VerifyOptions

async def authenticate_request(token: str, agent_id: str):
    options = VerifyOptions(required_permissions=["read:data"])
    
    try:
        context = await phlow.authenticate(token, agent_id, options)
        print(f"Authenticated agent: {context.agent.name}")
        return context
    except Exception as e:
        print(f"Authentication failed: {e}")
        return None
```

## Features

### JWT Token Operations

```python
from phlow_auth import generate_token, verify_token, decode_token

# Generate token for another agent
token = generate_token(
    agent_card=my_agent_card,
    private_key=my_private_key,
    audience="target-agent-id",
    expires_in="1h"
)

# Verify token
claims = verify_token(
    token=token,
    public_key=sender_public_key,
    audience="my-agent-id",
    issuer="sender-agent-id"
)

# Decode without verification
decoded = decode_token(token)
```

### Supabase Helpers

```python
from phlow_auth import SupabaseHelpers

helpers = SupabaseHelpers(supabase_client)

# Register agent card
await helpers.register_agent_card(agent_card)

# Get agent card
agent = await helpers.get_agent_card("agent-id")

# List agents with permissions
agents = await helpers.list_agent_cards(
    permissions=["read:data"],
    metadata_filters={"environment": "production"}
)

# Generate RLS policies
policy_sql = helpers.generate_rls_policy("my_table", "agent_access_policy")
```

### Rate Limiting

```python
from phlow_auth import PhlowConfig

config = PhlowConfig(
    # ... other config
    rate_limiting={
        "max_requests": 100,
        "window_ms": 60000  # 1 minute
    }
)
```

### Audit Logging

```python
# Enable in config
config = PhlowConfig(
    # ... other config
    enable_audit=True
)

# Audit events are automatically logged:
# - auth_success
# - auth_failure  
# - permission_denied
# - token_refresh
```

## Configuration

### Environment Variables

```bash
# Supabase
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=your-anon-key

# Agent Keys
AGENT_PUBLIC_KEY="-----BEGIN PUBLIC KEY-----\n...\n-----END PUBLIC KEY-----"
AGENT_PRIVATE_KEY="-----BEGIN RSA PRIVATE KEY-----\n...\n-----END RSA PRIVATE KEY-----"
```

### PhlowConfig Options

```python
config = PhlowConfig(
    supabase_url="...",
    supabase_anon_key="...",
    agent_card=AgentCard(...),
    private_key="...",
    
    # Optional settings
    token_expiry="1h",           # Default token expiration
    refresh_threshold=300,        # Refresh tokens expiring in 5 minutes
    enable_audit=True,           # Enable audit logging
    rate_limiting={              # Rate limiting configuration
        "max_requests": 100,
        "window_ms": 60000
    }
)
```

## Database Schema

Run this SQL in your Supabase project:

```sql
-- Agent Cards table
CREATE TABLE agent_cards (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  agent_id TEXT UNIQUE NOT NULL,
  name TEXT NOT NULL,
  description TEXT,
  permissions TEXT[] DEFAULT '{}',
  public_key TEXT NOT NULL,
  endpoints JSONB DEFAULT '{}',
  metadata JSONB DEFAULT '{}',
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Audit logs table
CREATE TABLE phlow_audit_logs (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
  event TEXT NOT NULL,
  agent_id TEXT NOT NULL,
  target_agent_id TEXT,
  details JSONB DEFAULT '{}',
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Enable RLS
ALTER TABLE agent_cards ENABLE ROW LEVEL SECURITY;
ALTER TABLE phlow_audit_logs ENABLE ROW LEVEL SECURITY;

-- Basic policies (customize as needed)
CREATE POLICY agent_cards_read ON agent_cards FOR SELECT USING (true);
CREATE POLICY agent_cards_own ON agent_cards FOR ALL USING (agent_id = auth.jwt() ->> 'sub');
CREATE POLICY audit_logs_own ON phlow_audit_logs FOR ALL USING (
  agent_id = auth.jwt() ->> 'sub' OR target_agent_id = auth.jwt() ->> 'sub'
);
```

## Error Handling

```python
from phlow_auth.exceptions import (
    AuthenticationError,
    AuthorizationError,
    TokenError,
    RateLimitError,
    ConfigurationError
)

try:
    context = await phlow.authenticate(token, agent_id)
except AuthenticationError as e:
    print(f"Auth failed: {e.message} (code: {e.code})")
except AuthorizationError as e:
    print(f"Access denied: {e.message}")
except RateLimitError as e:
    print(f"Rate limited: {e.message}")
```

## Async vs Sync

The library supports both async and sync operations:

```python
# Async (recommended)
context = await phlow.authenticate(token, agent_id)
await helpers.register_agent_card(agent_card)

# Sync
context = phlow.authenticate_sync(token, agent_id)
helpers.register_agent_card_sync(agent_card)
```

## Testing

```python
import pytest
from phlow_auth import PhlowMiddleware, PhlowConfig, AgentCard

@pytest.fixture
def phlow_middleware():
    config = PhlowConfig(
        supabase_url="http://localhost:54321",  # Local Supabase
        supabase_anon_key="test-key",
        agent_card=AgentCard(
            agent_id="test-agent",
            name="Test Agent",
            permissions=["read:data"],
            public_key="...",
        ),
        private_key="...",
    )
    return PhlowMiddleware(config)

@pytest.mark.asyncio
async def test_authentication(phlow_middleware):
    # Test authentication logic
    pass
```

## Development

```bash
# Clone the repository
git clone https://github.com/phlowai/phlow.git
cd phlow/packages/phlow-auth-python

# Install development dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Format code
black src tests
isort src tests

# Type checking
mypy src

# Linting
flake8 src tests
```

## License

MIT License - see LICENSE file for details.

## Support

- 📖 Documentation: https://github.com/phlowai/phlow#readme
- 🐛 Issues: https://github.com/phlowai/phlow/issues
- 💬 Discussions: https://github.com/phlowai/phlow/discussions