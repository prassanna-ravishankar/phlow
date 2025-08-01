# Role-Based Access Control (RBAC)

Phlow's RBAC system enables fine-grained access control using W3C Verifiable Credentials and cryptographic role verification.

## Overview

RBAC extends Phlow's authentication with role-based authorization, allowing agents to prove they possess specific roles through verifiable credentials.

```python
from phlow.integrations.fastapi import phlow_auth_role

@app.post("/admin-only")
async def admin_endpoint(
    context: PhlowContext = Depends(phlow_auth_role(middleware, "admin"))
):
    return {"message": "Admin access granted!"}
```

## How It Works

1. **Role Credentials**: Agents store W3C Verifiable Credentials containing role assertions
2. **Verification Flow**: Server requests role proof via A2A protocol
3. **Cryptographic Validation**: Credentials are verified using issuer's public key
4. **Caching**: Valid roles are cached in Supabase for performance

```mermaid
sequenceDiagram
    participant Client as Agent
    participant Server as Protected Service
    participant Cache as Supabase Cache

    Client->>Server: Request with JWT token
    Server->>Cache: Check cached role
    alt Role cached & valid
        Cache->>Server: Return cached role
    else Role not cached
        Server->>Client: Request role credential (A2A)
        Client->>Server: Verifiable Presentation
        Server->>Server: Verify credential signature
        Server->>Cache: Cache verified role
    end
    Server->>Client: Grant/deny access
```

## Core Components

### RoleCredentialStore
Client-side credential storage and management:

```python
from phlow.rbac import RoleCredentialStore

store = RoleCredentialStore()
await store.add_credential(admin_credential)

# Create cryptographically signed presentation for verification
presentation = await store.create_presentation(
    role="admin",
    holder_did="did:example:agent",
    challenge="optional-challenge-string"  # For additional security
)
```

### Middleware Integration
Server-side role verification:

```python
from phlow import PhlowMiddleware

middleware = PhlowMiddleware(config)

# Verify agent has specific role
context = await middleware.authenticate_with_role(token, "admin")
print(f"Agent has verified roles: {context.verified_roles}")
```

### FastAPI Integration
Protect endpoints with role requirements:

```python
from phlow.integrations.fastapi import FastAPIPhlowAuth

auth = FastAPIPhlowAuth(middleware)

@app.get("/manager-only")
async def manager_endpoint(
    context: PhlowContext = Depends(auth.create_role_auth_dependency("manager"))
):
    return {"authorized": True}
```

## Database Schema

RBAC adds multiple tables for comprehensive functionality:

```sql
-- Role verification cache
CREATE TABLE verified_roles (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    agent_id TEXT NOT NULL,
    role TEXT NOT NULL,
    verified_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    expires_at TIMESTAMP WITH TIME ZONE,
    credential_hash TEXT NOT NULL,
    issuer_did TEXT,
    metadata JSONB DEFAULT '{}',
    UNIQUE(agent_id, role)
);

-- DID public keys for cryptographic verification
CREATE TABLE did_public_keys (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    did TEXT NOT NULL,
    key_fragment TEXT NOT NULL,
    public_key TEXT NOT NULL, -- Base64 encoded public key
    key_type TEXT NOT NULL, -- 'Ed25519', 'RSA'
    UNIQUE(did, key_fragment)
);

-- Authentication audit logs
CREATE TABLE auth_audit_log (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    agent_id TEXT NOT NULL,
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
    event_type TEXT NOT NULL,
    success BOOLEAN NOT NULL,
    metadata JSONB DEFAULT '{}'
);
```

## Security Model

- **Cryptographic Verification**: All credentials verified using W3C standards
- **DID-based Identity**: Issuer and holder identification via DIDs
- **Expiration Handling**: Automatic cleanup of expired credentials
- **Row-Level Security**: Database policies restrict access to own roles

## Example Agent

See the complete [RBAC example agent](../examples/rbac_agent/) for a working implementation demonstrating:

- Role credential storage
- A2A message handling
- Protected endpoints
- Credential management

## Production Features

✅ **This implementation includes production-ready cryptographic verification and A2A messaging:**

1. **Full Cryptographic Verification**: Ed25519 and RSA signature verification using W3C standards
2. **Real A2A Messaging**: HTTP-based agent communication with endpoint resolution and error handling
3. **Secure Presentation Signing**: Cryptographic proof generation for verifiable presentations
4. **DID Document Caching**: Performance optimization with TTL-based caching
5. **Comprehensive Database Schema**: Complete with proper indexes and Row-Level Security policies

## Production Deployment Requirements

For production deployment, configure:

1. **Key Management**: Integrate with secure key management systems (HSM, vaults) for production DID keys
2. **Agent Registry**: Populate the `agent_cards` table with trusted agent endpoints
3. **Database Setup**: Deploy the complete schema from `docs/database-schema.sql`
4. **Monitoring**: Add logging and metrics for role verification flows
5. **Rate Limiting**: Configure request limits for A2A messaging endpoints

## API Reference

### phlow_auth_role()
```python
def phlow_auth_role(
    middleware: PhlowMiddleware,
    required_role: str,
    allow_expired: bool = False
) -> Callable
```

Create FastAPI dependency requiring specific role.

**Parameters:**
- `middleware`: PhlowMiddleware instance
- `required_role`: Role string (e.g., "admin", "manager")
- `allow_expired`: Whether to accept expired tokens

**Returns:** FastAPI dependency function

### authenticate_with_role()
```python
async def authenticate_with_role(
    self,
    token: str,
    required_role: str
) -> PhlowContext
```

Verify agent has required role credential.

**Parameters:**
- `token`: JWT authentication token
- `required_role`: Role to verify

**Returns:** PhlowContext with verified_roles populated

**Raises:** AuthenticationError if role verification fails
