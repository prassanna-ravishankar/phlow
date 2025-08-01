## Feature Specification: Phlow RBAC Extension

### 1\. Summary

Phlow RBAC is an enhancement to the existing Phlow authentication middleware that enables Role-Based Access Control (RBAC) using **Verifiable Credentials (VCs)**. It extends Phlow's current permission-based authentication with cryptographically verifiable role credentials.

This feature upgrades Phlow's existing `authenticate({ requiredPermissions: ['admin'] })` approach with `authenticateWithRole('admin')` - where roles are proven using verifiable credentials instead of simple JWT claims.

The extension does **not** enforce what a role can do; it only verifies that the user *has* a specific role. The application remains responsible for its own access control policies, just like the current Phlow system.

-----

### 2\. Core Components

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

### 3\. Phlow Middleware Extension

The RBAC functionality extends the existing `PhlowMiddleware` class with new methods for role-based authentication while maintaining full compatibility with the current API.

#### 3.1. Enhanced PhlowMiddleware (Server-Side Role Verification)

The enhanced middleware adds role-based authentication to existing Phlow functionality.

```python
# packages/phlow-auth-python/src/phlow_auth/middleware.py

from phlow_auth import PhlowMiddleware as BasePhlowMiddleware
from .rbac import RoleCredentialVerifier

class PhlowMiddleware(BasePhlowMiddleware):
    """Enhanced Phlow middleware with RBAC support."""

    def __init__(self, config: PhlowConfig):
        super().__init__(config)
        self.role_verifier = RoleCredentialVerifier(self.supabase)

    def authenticate_with_role(self, required_role: str):
        """
        Middleware that requests and verifies role credentials.

        Args:
            required_role: The role string to verify (e.g., 'admin').

        Returns:
            Middleware function for Express/FastAPI.
        """
        async def middleware(request):
            # 1. Perform standard Phlow authentication first
            context = await self.verify_token(self._extract_token(request))
            
            # 2. Check cache for previously verified role
            cached_role = await self._get_cached_role(
                context.agent.metadata['agent_id'], 
                required_role
            )
            
            if cached_role and not self._is_expired(cached_role):
                request.phlow = context
                return request
            
            # 3. Request role credential via A2A messaging
            role_response = await self.a2a_client.send_message(
                context.agent.metadata['agent_id'],
                {
                    "type": "role-credential-request",
                    "required_role": required_role,
                    "context": f"Access requires '{required_role}' role",
                    "nonce": self._generate_nonce()
                }
            )
            
            # 4. Verify the credential using your exact verification logic
            if role_response.get("presentation"):
                presentation = role_response["presentation"]
                is_valid = await self.role_verifier.verify_vc(presentation)
                
                if is_valid:
                    actual_role = self._extract_role_from_vc(presentation)
                    
                    if actual_role == required_role:
                        # 5. Cache the verified role in Supabase
                        await self._cache_verified_role(
                            context.agent.metadata['agent_id'],
                            required_role,
                            presentation
                        )
                        
                        request.phlow = context
                        return request
            
            raise AuthenticationError(f"Invalid or missing '{required_role}' role credential")
        
        return middleware

    async def verify_vc(self, presentation: dict) -> bool:
        """
        Cryptographically verify a Verifiable Credential presentation.
        
        This is your exact verification logic from the original spec.
        """
        return await self.role_verifier.verify_vc(presentation)

    async def _cache_verified_role(self, agent_id: str, role: str, presentation: dict):
        """Cache verified role credentials in Supabase."""
        await self.supabase.table('verified_roles').upsert({
            'agent_id': agent_id,
            'role': role,
            'verified_at': datetime.now().isoformat(),
            'credential_hash': self._hash_presentation(presentation),
            'expires_at': self._extract_expiry(presentation)
        })

    async def _get_cached_role(self, agent_id: str, role: str):
        """Retrieve cached role verification from Supabase."""
        result = await self.supabase.table('verified_roles').select('*').eq(
            'agent_id', agent_id
        ).eq('role', role).single()
        
        return result.data if result.data else None
```

#### 3.2. Client-Side Role Response Handler

For agents that need to respond to role credential requests, extend the existing A2A message handling.

```python
# Usage in agent code
class MyAgent:
    def __init__(self):
        self.phlow = PhlowMiddleware(config)
        self.credential_store = {}  # Store VCs locally
        
        # Register handler for role credential requests
        self.phlow.register_message_handler(
            'role-credential-request', 
            self._handle_role_request
        )
    
    async def _handle_role_request(self, message: dict) -> dict:
        """Handle incoming role credential requests."""
        requested_role = message.get('required_role')
        nonce = message.get('nonce')
        
        # 1. Find the role credential in local store
        role_vc = self.credential_store.get(requested_role)
        
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
    
    async def _create_presentation(self, vc: dict) -> dict:
        """Create and sign a Verifiable Presentation (your exact logic)."""
        return {
            "@context": ["https://www.w3.org/2018/credentials/v1"],
            "type": ["VerifiablePresentation"],
            "verifiableCredential": [vc],
            "holder": self.phlow.config.agent_card.metadata['agent_id'],
            "proof": await self._sign_presentation(vc)
        }
```

-----

### 4\. Feature Implementation

This feature would be implemented as an enhancement to the existing Phlow packages.

#### 4.1. Package Structure

**Python Package** (`packages/phlow-auth-python/`):
```
src/phlow_auth/
├── rbac/
│   ├── verifier.py           # VC verification logic  
│   ├── cache.py              # Supabase role caching
│   └── types.py              # RBAC-specific types
├── middleware.py             # Enhanced with authenticate_with_role()
└── __init__.py               # Export RBAC functionality
```

#### 4.2. Dependencies

**New Dependencies to Add:**
  * **VC Library:** For cryptographic verification of Verifiable Credentials
    * Python: `pyld`, `cryptography` for VC verification
  * **DID Resolution:** For resolving issuer DIDs to verification keys
    * Python: `did-python` or equivalent

**Existing Dependencies Leveraged:**
  * ✅ A2A client integration (already present)
  * ✅ Supabase integration (already present)
  * ✅ JWT handling (already present)
  * ✅ Middleware patterns (already present)

#### 4.3. Testing Strategy

**Integration Tests** (extending existing `tests/integration/`):
```python
# tests/integration/test_rbac.py
import pytest

class TestRBACIntegration:
    async def test_authenticate_with_valid_role_credential(self):
        # Test full RBAC flow using existing test infrastructure
        pass
    
    async def test_cache_verified_role_credentials(self):
        # Test Supabase caching functionality  
        pass
    
    async def test_handle_role_credential_requests(self):
        # Test A2A message exchange
        pass
```

**Database Schema** (extending existing Supabase setup):
```sql
-- Add to docs/database-schema.sql
CREATE TABLE verified_roles (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  agent_id TEXT NOT NULL,
  role TEXT NOT NULL,
  verified_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  expires_at TIMESTAMPTZ,
  credential_hash TEXT NOT NULL,
  metadata JSONB,
  UNIQUE(agent_id, role)
);
```

#### 4.4. Backwards Compatibility

The RBAC feature maintains full backwards compatibility:

```python
# Existing API continues to work unchanged
@app.post('/basic-endpoint')
@phlow.authenticate({'requiredPermissions': ['read:data']})

# New RBAC API works alongside
@app.post('/secure-endpoint') 
@phlow.authenticate_with_role('admin')

# Both can be used together
@app.post('/hybrid-endpoint')
@phlow.authenticate({'requiredPermissions': ['read:data']})
@phlow.authenticate_with_role('manager')
```

#### 4.5. Documentation Updates

**New Documentation Pages:**
  * `docs/guides/role-based-access.md` - RBAC implementation guide
  * `docs/concepts/verifiable-credentials.md` - VC concepts for agents
  * `docs/examples/rbac-agent.md` - Complete RBAC example

**Updated Documentation:**
  * `docs/api-reference.md` - Add RBAC methods
  * `README.md` - Mention RBAC capabilities
  * `docs/getting-started.md` - Include RBAC setup options

#### 4.6. Alignment with Phlow Roadmap

This RBAC feature aligns perfectly with Phlow's evolution toward an "Agent Marketplace Platform":

**Phase 1: Authentication Middleware (Current)**
- ✅ Basic JWT authentication *(existing)*
- ✅ Agent card storage *(existing)*
- 🔄 **Enhanced RBAC with VCs** *(this feature)*

**Phase 2: Agent Discovery & Registry (Next 6 months)**
- 🎯 **Role-based agent discovery** - Find agents by verified roles
- 🎯 **Capability matching** - Match agent skills with role requirements
- 🎯 **Trust scoring** - Factor in VC issuer reputation

**Phase 3: Agent Marketplace Platform (6-18 months)**
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
@phlow.authenticate_with_role('gdpr-compliant')  # Requires VC proof
async def handle_gdpr_data(request):
    # Process with confidence in compliance
```

This RBAC foundation enables the cryptographic trust layer that will power the entire agent marketplace ecosystem.
