# Getting Started with Phlow

Phlow is an Agent-to-Agent (A2A) authentication framework that makes it easy to secure communication between AI agents using JWT tokens and Supabase.

## Quick Start

### 1. Installation

Choose your language:

**JavaScript/TypeScript:**
```bash
npm install phlow-auth
```

**Python:**
```bash
pip install phlow-auth
```

**CLI Tools:**
```bash
npm install -g phlow-cli
```

### 2. Setup Supabase

1. Create a new Supabase project at [supabase.com](https://supabase.com)
2. In the SQL Editor, run the following schema:

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

-- Basic policies
CREATE POLICY agent_cards_read ON agent_cards FOR SELECT USING (true);
CREATE POLICY agent_cards_own ON agent_cards FOR ALL USING (agent_id = auth.jwt() ->> 'sub');
CREATE POLICY audit_logs_own ON phlow_audit_logs FOR ALL USING (
  agent_id = auth.jwt() ->> 'sub' OR target_agent_id = auth.jwt() ->> 'sub'
);
```

3. Get your project URL and anon key from Settings → API

### 3. Initialize Your Agent

**Using CLI (Recommended):**
```bash
# Initialize a new Phlow project
phlow init

# Generate and register agent card
phlow generate-card

# Start development environment
phlow dev-start
```

**Manual Setup:**
```javascript
// JavaScript/TypeScript
import { PhlowMiddleware, generateToken } from 'phlow-auth';

const phlow = new PhlowMiddleware({
  supabaseUrl: 'https://your-project.supabase.co',
  supabaseAnonKey: 'your-anon-key',
  agentCard: {
    agentId: 'my-agent',
    name: 'My Agent',
    permissions: ['read:data', 'write:data'],
    publicKey: '-----BEGIN PUBLIC KEY-----\\n...\\n-----END PUBLIC KEY-----',
  },
  privateKey: '-----BEGIN RSA PRIVATE KEY-----\\n...\\n-----END RSA PRIVATE KEY-----',
  options: {
    enableAudit: true,
  },
});
```

```python
# Python
from phlow_auth import PhlowMiddleware, PhlowConfig, AgentCard

config = PhlowConfig(
    supabase_url="https://your-project.supabase.co",
    supabase_anon_key="your-anon-key",
    agent_card=AgentCard(
        agent_id="my-agent",
        name="My Agent",
        permissions=["read:data", "write:data"],
        public_key="-----BEGIN PUBLIC KEY-----\\n...\\n-----END PUBLIC KEY-----",
    ),
    private_key="-----BEGIN RSA PRIVATE KEY-----\\n...\\n-----END RSA PRIVATE KEY-----",
    enable_audit=True,
)

phlow = PhlowMiddleware(config)
```

### 4. Protect Your Endpoints

**Express.js:**
```javascript
import express from 'express';

const app = express();

// Protected route
app.get('/protected', phlow.authenticate(), (req, res) => {
  res.json({
    message: 'Access granted!',
    agent: req.phlow.agent.name,
    permissions: req.phlow.claims.permissions,
  });
});
```

**FastAPI:**
```python
from fastapi import FastAPI, Depends
from phlow_auth.integrations.fastapi import create_phlow_dependency

app = FastAPI()
auth_required = create_phlow_dependency(phlow)

@app.get("/protected")
async def protected_endpoint(context = Depends(auth_required)):
    return {
        "message": "Access granted!",
        "agent": context.agent.name,
        "permissions": context.claims.permissions
    }
```

### 5. Make Authenticated Requests

```javascript
// Generate token for another agent
const token = generateToken(
  myAgentCard,
  myPrivateKey,
  'target-agent-id',
  '1h'
);

// Make request
const response = await fetch('http://target-agent:3000/protected', {
  headers: {
    'Authorization': `Bearer ${token}`,
    'X-Phlow-Agent-Id': 'my-agent-id',
  },
});
```

```python
# Generate token for another agent
from phlow_auth import generate_token

token = generate_token(
    my_agent_card,
    my_private_key,
    "target-agent-id",
    "1h"
)

# Make request
import requests

response = requests.get(
    "http://target-agent:3000/protected",
    headers={
        "Authorization": f"Bearer {token}",
        "X-Phlow-Agent-Id": "my-agent-id",
    }
)
```

## Core Concepts

### Agent Cards
Agent cards contain identity and permission information:

```javascript
const agentCard = {
  agentId: 'unique-agent-identifier',
  name: 'Human-readable name',
  description: 'Optional description',
  permissions: ['read:data', 'write:data', 'admin:users'],
  publicKey: 'RSA public key in PEM format',
  endpoints: {
    api: 'http://agent-url:3000',
    health: 'http://agent-url:3000/health',
  },
  metadata: {
    environment: 'production',
    version: '1.0.0',
  },
};
```

### JWT Tokens
Phlow uses RS256-signed JWT tokens with these claims:

- `sub`: Subject (agent ID)
- `iss`: Issuer (agent ID)  
- `aud`: Audience (target agent ID)
- `exp`: Expiration time
- `iat`: Issued at time
- `permissions`: Array of permissions
- `metadata`: Optional metadata

### Permissions
Permissions follow a namespace:action pattern:

- `read:data` - Read data operations
- `write:data` - Write data operations
- `admin:users` - User administration
- `admin:agents` - Agent administration
- `audit:logs` - Access audit logs

## Authentication Flow

1. **Client Agent** generates a JWT token signed with their private key
2. **Token includes**:
   - Client's agent ID (issuer)
   - Target agent ID (audience)
   - Client's permissions
   - Expiration time
3. **Target Agent** receives the request and:
   - Extracts the agent ID from headers
   - Looks up the client's public key from Supabase
   - Verifies the JWT signature
   - Checks permissions and expiration
4. **Access granted** if all checks pass

## Configuration Options

### JavaScript/TypeScript
```javascript
const phlow = new PhlowMiddleware({
  supabaseUrl: 'https://your-project.supabase.co',
  supabaseAnonKey: 'your-anon-key',
  agentCard: myAgentCard,
  privateKey: myPrivateKey,
  options: {
    tokenExpiry: '1h',           // Default token expiration
    refreshThreshold: 300,       // Refresh tokens expiring in 5 minutes
    enableAudit: true,          // Enable audit logging
    rateLimiting: {             // Rate limiting configuration
      maxRequests: 100,
      windowMs: 60000,          // 1 minute
    },
  },
});
```

### Python
```python
config = PhlowConfig(
    supabase_url="https://your-project.supabase.co",
    supabase_anon_key="your-anon-key",
    agent_card=my_agent_card,
    private_key=my_private_key,
    token_expiry="1h",
    refresh_threshold=300,
    enable_audit=True,
    rate_limiting={
        "max_requests": 100,
        "window_ms": 60000,
    }
)
```

## Environment Variables

```bash
# Supabase Configuration
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=your-anon-key

# Agent Configuration
AGENT_ID=my-agent
AGENT_NAME=My Agent
AGENT_DESCRIPTION=Optional description
AGENT_PERMISSIONS=read:data,write:data

# Agent Keys (generate with: phlow init)
AGENT_PUBLIC_KEY="-----BEGIN PUBLIC KEY-----\\n...\\n-----END PUBLIC KEY-----"
AGENT_PRIVATE_KEY="-----BEGIN RSA PRIVATE KEY-----\\n...\\n-----END RSA PRIVATE KEY-----"

# Optional Settings
PORT=3000
```

## Development Tools

### CLI Commands

```bash
# Initialize new project
phlow init

# Generate and register agent card
phlow generate-card --output agent-card.json

# Start development environment
phlow dev-start --port 3000

# Generate test tokens
phlow test-token --target target-agent-id --expires 1h
```

### Local Testing

Use the development utilities:

```javascript
import { DevServer, TestRunner } from 'phlow-dev';

// Start development server with test scenarios
const devServer = new DevServer({
  port: 3000,
  enableTestEndpoints: true,
  mockAgents: [agentCard1, agentCard2],
});

await devServer.start();

// Run test scenarios
const testRunner = new TestRunner();
const results = await testRunner.runAllScenarios();
```

## Next Steps

- 📖 Read the [API Reference](./api-reference.md)
- 🔍 Explore [Examples](../examples/)
- 🧪 Run [Integration Tests](../tests/integration/)
- 💬 Join [Discussions](https://github.com/phlowai/phlow/discussions)

## Common Patterns

### Permission-Based Access Control
```javascript
// Require specific permissions
app.get('/admin', phlow.authenticate({ 
  requiredPermissions: ['admin:users'] 
}), handler);

// Multiple permission options
app.get('/data', phlow.authenticate({ 
  requiredPermissions: ['read:data', 'admin:all'] 
}), handler);
```

### Agent Discovery
```javascript
import { SupabaseHelpers } from 'phlow-auth';

const helpers = new SupabaseHelpers(supabaseClient);

// Find agents with specific permissions
const dataAgents = await helpers.listAgentCards(['read:data']);

// Find agents by metadata
const prodAgents = await helpers.listAgentCards(
  undefined, 
  { environment: 'production' }
);
```

### Error Handling
```javascript
app.use((error, req, res, next) => {
  if (error.name === 'AuthenticationError') {
    return res.status(401).json({
      error: 'Authentication failed',
      code: error.code,
    });
  }
  
  if (error.name === 'AuthorizationError') {
    return res.status(403).json({
      error: 'Insufficient permissions',
      required: error.requiredPermissions,
    });
  }
  
  // Handle other errors...
});
```

## Security Best Practices

1. **Keep private keys secure** - Never commit them to version control
2. **Use short token expiration** - Default 1 hour is recommended
3. **Enable audit logging** - Track all authentication events
4. **Implement rate limiting** - Prevent abuse
5. **Use HTTPS** - Encrypt all communications
6. **Rotate keys regularly** - Update keys periodically
7. **Minimal permissions** - Grant only necessary permissions
8. **Monitor audit logs** - Watch for suspicious activity

## Troubleshooting

### Common Issues

**"Agent not found"**
- Ensure the agent card is registered in Supabase
- Check that the agent ID matches exactly

**"Invalid token"**
- Verify the token is properly signed with the correct private key
- Check that the public key in Supabase matches the private key
- Ensure the token hasn't expired

**"Insufficient permissions"**
- Check that the agent has the required permissions
- Verify permissions are correctly specified in the agent card

**"Rate limit exceeded"**
- Implement backoff and retry logic
- Consider increasing rate limits if appropriate
- Check for potential infinite loops or excessive requests

### Debug Mode

Enable debug logging:

```bash
# JavaScript/Node.js
DEBUG=phlow:* npm start

# Python
import logging
logging.getLogger('phlow_auth').setLevel(logging.DEBUG)
```

### Health Checks

Implement health checks for monitoring:

```javascript
app.get('/health', (req, res) => {
  res.json({
    status: 'healthy',
    agent: process.env.AGENT_ID,
    timestamp: new Date().toISOString(),
    uptime: process.uptime(),
  });
});
```