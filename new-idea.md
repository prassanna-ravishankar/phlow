## Feature Specification: Phlow RBAC Extension

### 1. Summary

Phlow RBAC is an enhancement to the existing Phlow authentication middleware that enables Role-Based Access Control (RBAC) using **Verifiable Credentials (VCs)**. It extends Phlow's current permission-based authentication with cryptographically verifiable role credentials.

This feature upgrades Phlow's existing `@phlow_auth(required_permissions=['admin'])` approach with `@phlow_auth_role('admin')` - where roles are proven using verifiable credentials instead of simple JWT claims.

The extension does **not** enforce what a role can do; it only verifies that the agent *has* a specific role. The application remains responsible for its own access control policies, just like the current Phlow system.

-----

### 2. Core Components

#### 2.1. The Role Credential Profile

A dedicated Verifiable Credential format for asserting a role.

  * **Type:** `RoleCredential`
  * **Claims:** The `credentialSubject` MUST contain a `role` property (a string) or a `roles` property (an array of strings).

**Example `RoleCredential` JSON:**

```json
{
  "@context": [
    "https://www.w3.org/2018/credentials/v1",
    "https://www.w3.org/2018/credentials/examples/v1"
  ],
  "id": "http://example.edu/credentials/3732",
  "type": ["VerifiableCredential", "RoleCredential"],
  "issuer": "did:example:123456789",
  "issuanceDate": "2025-08-01T12:01:00Z",
  "credentialSubject": {
    "id": "did:example:abcdefgh",
    "role": "admin"
  }
}
```

#### 2.2. A2A Message-Based Role Exchange

A simple message exchange using Phlow's existing A2A client infrastructure to handle the request and presentation of role credentials.

  * **Transport:** Phlow's existing A2A messaging system (no new protocol needed)
  * **Roles:** `verifier` (requests the role proof) and `holder` (presents the role credential).

**Messages:**

1.  **`role-credential-request`**

      * **Type:** Standard A2A message with type `role-credential-request`
      * **Sender:** `verifier` (the Phlow-protected service)
      * **Recipient:** `holder` (the calling agent)
      * **Purpose:** Asks the calling agent to provide a credential proving they have a specific role.

    **JSON Body:**

    ```json
    {
      "type": "role-credential-request",
      "required_role": "admin",
      "context": "Access to the 'delete-records' endpoint requires the 'admin' role.",
      "nonce": "unique-request-id-123"
    }
    ```

2.  **`role-credential-response`**

      * **Type:** Standard A2A message with type `role-credential-response`
      * **Sender:** `holder` (the calling agent)
      * **Recipient:** `verifier` (the Phlow-protected service)
      * **Purpose:** Delivers the `RoleCredential` inside a standard Verifiable Presentation.

    **JSON Body:**

    ```json
    {
      "type": "role-credential-response",
      "nonce": "unique-request-id-123",
      "presentation": {
        "@context": ["https://www.w3.org/2018/credentials/v1"],
        "type": ["VerifiablePresentation"],
        "verifiableCredential": [
          {
            /* The full RoleCredential JSON from section 2.1 goes here */
          }
        ],
        "holder": "did:example:abcdefgh",
        "proof": { /* ...signature proof... */ }
      }
    }
    ```

-----

### 3. Phlow Middleware Extension

The RBAC functionality extends the existing `PhlowMiddleware` class with new methods for role-based authentication while maintaining full compatibility with the current API.

#### 3.1. Enhanced PhlowMiddleware (Server-Side Role Verification)

The enhanced middleware adds role-based authentication to existing Phlow functionality.

```python
# src/phlow/middleware.py

from datetime import datetime, timezone
from .rbac import RoleCredentialVerifier

class PhlowMiddleware:
    """Enhanced Phlow middleware with RBAC support."""

    def __init__(self, config: PhlowConfig):
        super().__init__(config)
        self.role_verifier = RoleCredentialVerifier(self.supabase)

    async def authenticate_with_role(self, token: str, required_role: str) -> PhlowContext:
        """
        Authenticate and verify role credentials.

        Args:
            token: JWT token
            required_role: The role string to verify (e.g., 'admin').

        Returns:
            PhlowContext with verified role information

        Raises:
            AuthenticationError: If authentication or role verification fails
        """
        # 1. Perform standard Phlow authentication first
        context = self.verify_token(token)
        
        # 2. Check cache for previously verified role
        agent_id = context.agent.metadata.get('agent_id')
        cached_role = await self._get_cached_role(agent_id, required_role)
        
        if cached_role and not self._is_expired(cached_role):
            context.verified_roles = [required_role]
            return context
        
        # 3. Request role credential via A2A messaging
        role_response = await self.a2a_client.send_message(
            recipient_did=agent_id,
            message={
                "type": "role-credential-request",
                "required_role": required_role,
                "context": f"Access requires '{required_role}' role",
                "nonce": self._generate_nonce()
            }
        )
        
        # 4. Verify the credential
        if role_response.get("presentation"):
            presentation = role_response["presentation"]
            is_valid = await self.role_verifier.verify_vc(presentation)
            
            if is_valid:
                actual_role = self._extract_role_from_vc(presentation)
                
                if actual_role == required_role:
                    # 5. Cache the verified role in Supabase
                    await self._cache_verified_role(
                        agent_id,
                        required_role,
                        presentation
                    )
                    
                    context.verified_roles = [required_role]
                    return context
        
        raise AuthenticationError(f"Invalid or missing '{required_role}' role credential")

    async def _cache_verified_role(self, agent_id: str, role: str, presentation: dict):
        """Cache verified role credentials in Supabase."""
        await self.supabase.table('verified_roles').upsert({
            'agent_id': agent_id,
            'role': role,
            'verified_at': datetime.now(timezone.utc).isoformat(),
            'credential_hash': self._hash_presentation(presentation),
            'expires_at': self._extract_expiry(presentation)
        }).execute()

    async def _get_cached_role(self, agent_id: str, role: str):
        """Retrieve cached role verification from Supabase."""
        result = await self.supabase.table('verified_roles').select('*').eq(
            'agent_id', agent_id
        ).eq('role', role).single().execute()
        
        return result.data if result.data else None
```

#### 3.2. FastAPI Integration Enhancement

Extend the existing FastAPI integration with role-based authentication.

```python
# src/phlow/integrations/fastapi.py

def phlow_auth_role(
    required_role: str,
    allow_expired: bool = False,
) -> Callable:
    """
    Create a FastAPI dependency for role-based authentication.

    Args:
        required_role: Role required for access
        allow_expired: Allow expired tokens (default: False)

    Returns:
        FastAPI dependency function
    """
    async def verify_role(
        request: Request,
        authorization: str = Header(..., alias="Authorization"),
    ) -> PhlowContext:
        # Extract token
        if not authorization.startswith("Bearer "):
            raise HTTPException(
                status_code=401,
                detail="Invalid authorization header"
            )
        
        token = authorization.replace("Bearer ", "")
        
        # Get middleware from app state
        middleware = request.app.state.phlow_middleware
        
        try:
            context = await middleware.authenticate_with_role(token, required_role)
            return context
        except AuthenticationError as e:
            raise HTTPException(status_code=401, detail=str(e))
        except Exception as e:
            logger.error(f"Role verification error: {e}")
            raise HTTPException(status_code=500, detail="Internal server error")
    
    return Depends(verify_role)

# Usage example:
@app.post("/admin/delete")
async def delete_records(
    context: PhlowContext = phlow_auth_role("admin")
):
    # Only accessible by agents with verified admin role
    return {"message": "Records deleted"}
```

#### 3.3. Client-Side Role Response Handler

For agents that need to respond to role credential requests, extend the existing A2A message handling.

```python
# Example agent implementation
from phlow import PhlowMiddleware
from phlow.rbac import RoleCredentialStore

class MyAgent:
    def __init__(self):
        self.phlow = PhlowMiddleware(config)
        self.credential_store = RoleCredentialStore()  # Store VCs locally
        
        # Register handler for role credential requests
        self.phlow.a2a_client.register_handler(
            'role-credential-request', 
            self._handle_role_request
        )
    
    async def _handle_role_request(self, message: dict) -> dict:
        """Handle incoming role credential requests."""
        requested_role = message.get('required_role')
        nonce = message.get('nonce')
        
        # 1. Find the role credential in local store
        role_vc = await self.credential_store.get_credential(requested_role)
        
        if not role_vc:
            return {
                "type": "role-credential-response", 
                "nonce": nonce,
                "error": f"Role '{requested_role}' not available"
            }
        
        # 2. Create and sign the Verifiable Presentation
        presentation = await self._create_presentation(role_vc)
        
        # 3. Return the credential
        return {
            "type": "role-credential-response",
            "nonce": nonce, 
            "presentation": presentation
        }
```

-----

### 4. Feature Implementation

This feature would be implemented as an enhancement to the existing Phlow packages.

#### 4.1. Package Structure

**Python Package** (`src/phlow/`):
```
src/phlow/
├── rbac/
│   ├── __init__.py
│   ├── verifier.py           # VC verification logic  
│   ├── cache.py              # Supabase role caching
│   ├── store.py              # Client-side credential storage
│   └── types.py              # RBAC-specific types
├── middleware.py             # Enhanced with authenticate_with_role()
├── integrations/
│   └── fastapi.py           # Enhanced with phlow_auth_role()
└── __init__.py              # Export RBAC functionality
```

#### 4.2. Dependencies

**New Dependencies to Add:**
```toml
[project.optional-dependencies]
rbac = [
    "pyld>=2.0.0",           # JSON-LD processing for VCs
    "cryptography>=41.0.0",   # Enhanced crypto operations
    "didkit>=0.3.0",         # DID resolution and VC verification
]
```

**Existing Dependencies Leveraged:**
  * ✅ A2A client integration (already present)
  * ✅ Supabase integration (already present)
  * ✅ JWT handling (already present)
  * ✅ Middleware patterns (already present)

#### 4.3. Testing Strategy

**Integration Tests** (extending existing `tests/`):
```python
# tests/test_rbac.py
import pytest
from phlow.rbac import RoleCredentialVerifier

class TestRBACIntegration:
    async def test_authenticate_with_valid_role_credential(self):
        # Test full RBAC flow using existing test infrastructure
        middleware = PhlowMiddleware(test_config)
        context = await middleware.authenticate_with_role(token, "admin")
        assert "admin" in context.verified_roles
    
    async def test_cache_verified_role_credentials(self):
        # Test Supabase caching functionality  
        pass
    
    async def test_handle_role_credential_requests(self):
        # Test A2A message exchange
        pass
```

**Database Schema** (add to existing `docs/database-schema.sql`):
```sql
-- Table for caching verified role credentials
CREATE TABLE verified_roles (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  agent_id TEXT NOT NULL,
  role TEXT NOT NULL,
  verified_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  expires_at TIMESTAMPTZ,
  credential_hash TEXT NOT NULL,
  issuer_did TEXT,
  metadata JSONB,
  UNIQUE(agent_id, role)
);

-- Index for efficient lookups
CREATE INDEX idx_verified_roles_agent_role ON verified_roles(agent_id, role);
CREATE INDEX idx_verified_roles_expires ON verified_roles(expires_at);
```

#### 4.4. Backwards Compatibility

The RBAC feature maintains full backwards compatibility:

```python
# Existing API continues to work unchanged
@app.post('/basic-endpoint')
async def basic(context: PhlowContext = phlow_auth(required_permissions=['read:data'])):
    return {"status": "ok"}

# New RBAC API works alongside
@app.post('/secure-endpoint') 
async def secure(context: PhlowContext = phlow_auth_role('admin')):
    return {"status": "ok"}

# Both can be used together
@app.post('/hybrid-endpoint')
async def hybrid(
    context: PhlowContext = phlow_auth(required_permissions=['read:data']),
    role_context: PhlowContext = phlow_auth_role('manager')
):
    return {"status": "ok"}
```

#### 4.5. Documentation Updates

**New Documentation Pages:**
  * `docs/guides/role-based-access.md` - RBAC implementation guide
  * `docs/concepts/verifiable-credentials.md` - VC concepts for agents
  * `docs/examples/rbac-agent/` - Complete RBAC example

**Updated Documentation:**
  * `docs/api-reference.md` - Add RBAC methods
  * `README.md` - Mention RBAC capabilities
  * `docs/quickstart.md` - Include RBAC setup options

#### 4.6. Alignment with Phlow Roadmap

This RBAC feature aligns perfectly with Phlow's evolution toward an "Agent Marketplace Platform":

**Phase 1: Authentication Middleware (Current)**
- ✅ Basic JWT authentication *(existing)*
- ✅ Agent card storage *(existing)*
- 🔄 **Enhanced RBAC with VCs** *(this feature)*

**Phase 2: Agent Discovery & Registry**
- 🎯 **Role-based agent discovery** - Find agents by verified roles
- 🎯 **Capability matching** - Match agent skills with role requirements
- 🎯 **Trust scoring** - Factor in VC issuer reputation

**Phase 3: Agent Marketplace Platform**
- 🎯 **Role-based pricing** - Different rates for different certified roles
- 🎯 **Compliance verification** - Cryptographic proof of certifications
- 🎯 **Reputation systems** - Track performance by verified role

**Marketplace Benefits:**
```python
# Agents can advertise verified capabilities
agent_card = {
  "name": "Certified Data Analyst",
  "skills": ["data-analysis", "machine-learning"],
  "verified_roles": ["iso-27001-certified", "gdpr-compliant"],  # VC-backed
  "pricing": {
    "basic-analysis": 10,
    "certified-analysis": 25  # Premium for verified compliance
  }
}

# Consumers can request specific compliance levels
@app.post('/sensitive-data-analysis')
async def handle_gdpr_data(
    context: PhlowContext = phlow_auth_role('gdpr-compliant')
):
    # Process with confidence in compliance
    return {"status": "analysis complete"}
```

This RBAC foundation enables the cryptographic trust layer that will power the entire agent marketplace ecosystem.