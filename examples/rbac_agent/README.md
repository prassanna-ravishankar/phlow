# Phlow RBAC Agent Example

This example demonstrates how to build an agent that uses Phlow's Role-Based Access Control (RBAC) functionality with Verifiable Credentials.

## Features Demonstrated

- **Role-Based Authentication**: Protect endpoints with specific role requirements
- **Verifiable Credentials**: Use cryptographically verifiable role credentials
- **A2A Protocol Integration**: Handle role credential requests from other agents
- **Credential Management**: Store and manage role credentials locally
- **Multi-Role Support**: Support multiple roles per agent

## Quick Start

### 1. Prerequisites

- Python 3.10+
- Supabase project with Phlow schema
- Basic understanding of FastAPI and A2A Protocol

### 2. Installation

```bash
# Install dependencies
pip install -r requirements.txt

# Or install Phlow with RBAC support
pip install "phlow[rbac]"
```

### 3. Configuration

Set up your environment variables:

```bash
# Supabase configuration
export SUPABASE_URL="https://your-project.supabase.co"
export SUPABASE_ANON_KEY="your-anon-key"

# Agent configuration
export AGENT_ID="rbac-demo-agent"
export AGENT_NAME="RBAC Demo Agent"
export PRIVATE_KEY="your-private-key"
```

Or create a `.env` file:

```env
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=your-anon-key
AGENT_ID=rbac-demo-agent
AGENT_NAME=RBAC Demo Agent
PRIVATE_KEY=your-private-key
```

### 4. Database Setup

Ensure your Supabase project has the Phlow schema with RBAC tables:

```sql
-- This should be included in your Phlow schema
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
```

### 5. Run the Agent

```bash
python main.py
```

The agent will be available at:
- **API**: http://localhost:8000
- **Documentation**: http://localhost:8000/docs
- **A2A Discovery**: http://localhost:8000/.well-known/agent.json

## API Endpoints

### Public Endpoints

- `GET /public` - No authentication required
- `GET /health` - Health check
- `GET /status` - Agent status and configuration

### Authenticated Endpoints

- `GET /basic-auth` - Basic Phlow authentication
- `GET /admin-only` - Requires admin role credential
- `GET /manager-only` - Requires manager role credential
- `POST /secure-operation` - Admin-only secure operations

### Role Management

- `GET /roles` - List available roles
- `GET /roles/{role}` - Get role information

### A2A Protocol

- `GET /.well-known/agent.json` - Agent discovery
- `POST /tasks/send` - Handle A2A tasks and role credential requests

## Usage Examples

### 1. Public Access

```bash
curl http://localhost:8000/public
```

### 2. Basic Authentication

```bash
# Get a JWT token first (implementation-specific)
curl -H "Authorization: Bearer YOUR_JWT_TOKEN" \
     http://localhost:8000/basic-auth
```

### 3. Role-Based Access

```bash
# Admin-only endpoint (requires admin role credential)
curl -H "Authorization: Bearer YOUR_JWT_TOKEN" \
     http://localhost:8000/admin-only

# Manager-only endpoint (requires manager role credential)
curl -H "Authorization: Bearer YOUR_JWT_TOKEN" \
     http://localhost:8000/manager-only
```

### 4. Role Credential Request (A2A)

```bash
# Request admin role credential from this agent
curl -X POST http://localhost:8000/tasks/send \
     -H "Content-Type: application/json" \
     -d '{
       "type": "role-credential-request",
       "required_role": "admin",
       "nonce": "test-nonce-123",
       "context": "Need admin access for secure operation"
     }'
```

## How It Works

### 1. Role Credential Storage

The agent stores role credentials locally using `RoleCredentialStore`:

```python
# Sample credential structure
{
  "@context": ["https://www.w3.org/2018/credentials/v1"],
  "id": "http://example.org/credentials/admin/123",
  "type": ["VerifiableCredential", "RoleCredential"],
  "issuer": "did:example:issuer",
  "issuanceDate": "2025-08-01T12:00:00Z",
  "credentialSubject": {
    "id": "did:example:rbac-demo-agent",
    "role": "admin"
  }
}
```

### 2. Role-Based Route Protection

Routes are protected using FastAPI dependencies:

```python
@app.get("/admin-only")
async def admin_endpoint(
    context: PhlowContext = Depends(auth.create_role_auth_dependency("admin"))
):
    return {"message": "Admin access granted!"}
```

### 3. Role Credential Exchange

When another agent needs to verify this agent's role:

1. **Request**: Other agent sends `role-credential-request`
2. **Lookup**: This agent checks its credential store
3. **Presentation**: Creates a Verifiable Presentation
4. **Response**: Returns the presentation or error

### 4. Verification Process

When this agent accesses role-protected endpoints:

1. **Cache Check**: Look for cached role verification
2. **Request**: If not cached, request credential from agent
3. **Verify**: Cryptographically verify the credential
4. **Cache**: Store successful verification
5. **Access**: Grant access to protected resource

## Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Client Agent  │    │  RBAC Demo Agent │    │   Supabase      │
│                 │    │                  │    │                 │
│  ┌───────────┐  │    │  ┌─────────────┐ │    │  ┌───────────┐  │
│  │ JWT Token │  │    │  │ Middleware  │ │    │  │ Agent     │  │
│  └───────────┘  │    │  └─────────────┘ │    │  │ Cards     │  │
│                 │    │                  │    │  └───────────┘  │
│  ┌───────────┐  │───▶│  ┌─────────────┐ │◄──▶│  ┌───────────┐  │
│  │ Role      │  │    │  │ RBAC        │ │    │  │ Verified  │  │
│  │ Request   │  │    │  │ Verifier    │ │    │  │ Roles     │  │
│  └───────────┘  │    │  └─────────────┘ │    │  └───────────┘  │
│                 │    │                  │    │                 │
└─────────────────┘    │  ┌─────────────┐ │    └─────────────────┘
                       │  │ Credential  │ │    
                       │  │ Store       │ │    
                       │  └─────────────┘ │    
                       └──────────────────┘    
```

## Sample Credentials

The agent comes with sample credentials for demonstration:

- **Admin Role**: Full administrative access
- **Manager Role**: Management-level access

In production, these would be:
- Issued by trusted credential authorities
- Cryptographically signed
- Have proper expiration dates
- Include additional metadata

## Security Considerations

⚠️ **This is a demo implementation**

For production use, ensure:

1. **Proper Key Management**: Use secure key storage
2. **Credential Verification**: Implement full cryptographic verification
3. **Issuer Trust**: Only accept credentials from trusted issuers
4. **Expiration Handling**: Properly handle credential expiration
5. **Audit Logging**: Log all authentication events
6. **Network Security**: Use HTTPS in production

## Extending the Example

### Adding New Roles

1. Create new credentials in `setup_sample_credentials()`
2. Add new protected endpoints
3. Update role management endpoints

### Custom Verification Logic

Extend `RoleCredentialVerifier` to add:
- Issuer trust policies
- Custom verification rules
- Integration with external PKI

### Advanced A2A Integration

Implement full A2A protocol support:
- Agent discovery and resolution
- Bi-directional messaging
- Task orchestration

## Troubleshooting

### Common Issues

1. **"Authorization header required"**
   - Make sure to include Bearer token in requests

2. **"Role not verified"**
   - Check if the agent has the required role credential
   - Verify credential is not expired

3. **"Agent ID not found"**
   - Ensure JWT token contains agent_id in metadata

4. **Database connection errors**
   - Verify Supabase credentials
   - Check network connectivity

### Debug Mode

Run with debug logging:

```bash
# Set log level
export LOG_LEVEL=DEBUG
python main.py
```

### Testing Endpoints

Use the built-in FastAPI docs at http://localhost:8000/docs to test endpoints interactively.

## Next Steps

- Integrate with real credential issuers
- Implement full cryptographic verification
- Add more sophisticated role hierarchies
- Deploy to production environment
- Integrate with agent marketplace

## Support

For issues and questions:
- Check the main Phlow documentation
- Review the RBAC specification
- Open issues on the Phlow GitHub repository