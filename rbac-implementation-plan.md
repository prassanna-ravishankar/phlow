# Phlow RBAC Implementation Plan

## Overview
Implement Role-Based Access Control using Verifiable Credentials (VCs) as an enhancement to Phlow's existing permission-based authentication.

## Key Updates from Original Spec

### 1. API Alignment
- Current: `phlow_auth(required_permissions=['admin'])`
- New: Add `phlow_auth_role('admin')` or extend existing decorator

### 2. Simplified Architecture
Since Phlow has evolved to pure Python with A2A integration:
- Leverage existing A2A client for credential exchange
- Use existing Supabase integration for caching
- Extend current `PhlowMiddleware` class

### 3. Implementation Steps

#### Phase 1: Core RBAC Module
```python
# src/phlow/rbac/__init__.py
from .verifier import RoleCredentialVerifier
from .types import RoleCredential, VerifiablePresentation
```

#### Phase 2: Middleware Extension
```python
# src/phlow/middleware.py
class PhlowMiddleware:
    # ... existing code ...
    
    async def authenticate_with_role(self, required_role: str):
        """Verify agent has a specific role via VC."""
        # Implementation following the spec
```

#### Phase 3: FastAPI Integration
```python
# src/phlow/integrations/fastapi.py
def phlow_auth_role(required_role: str):
    """Decorator for role-based authentication."""
    # Implementation
```

### 4. Database Schema Addition
```sql
-- Add to existing Supabase schema
CREATE TABLE verified_roles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_id TEXT NOT NULL,
    role TEXT NOT NULL,
    verified_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at TIMESTAMPTZ,
    credential_hash TEXT NOT NULL,
    issuer_did TEXT,
    UNIQUE(agent_id, role)
);
```

### 5. Benefits for Agent Marketplace
- **Trust Layer**: Cryptographic proof of agent capabilities
- **Premium Tiers**: Different pricing for verified roles
- **Compliance**: Verifiable regulatory compliance (GDPR, HIPAA)
- **Discovery**: Find agents by certified capabilities

### 6. Example Usage
```python
# Agent with verified roles
@app.post("/financial-analysis")
@phlow_auth_role("certified-financial-analyst")
async def analyze_portfolio(request: Request):
    # Only accessible by agents with verified financial analyst credentials
    pass

# Combined auth (permissions + role)
@app.post("/admin-action")
@phlow_auth(required_permissions=["write:data"])
@phlow_auth_role("admin")
async def admin_endpoint(request: Request):
    # Requires both permission and verified admin role
    pass
```

### 7. Dependencies to Add
```toml
[project.optional-dependencies]
rbac = [
    "pyld>=2.0.0",  # JSON-LD processing for VCs
    "cryptography>=41.0.0",  # Enhanced crypto operations
    "did-resolver>=0.1.0",  # DID resolution
]
```

## Implementation Priority
Given Phlow's roadmap toward an Agent Marketplace, this RBAC feature is high priority as it:
1. Enables trust-based agent discovery
2. Supports premium pricing models
3. Provides compliance verification
4. Differentiates Phlow from simple auth solutions

## Next Steps
1. Create `src/phlow/rbac/` module structure
2. Implement VC verification logic
3. Extend middleware with role authentication
4. Add database migrations
5. Create comprehensive examples
6. Update documentation