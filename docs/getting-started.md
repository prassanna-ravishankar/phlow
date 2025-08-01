# Getting Started with Phlow

Phlow provides simple JWT authentication for AI agent networks, fully compatible with the [A2A Protocol](https://a2aproject.github.io/A2A/latest/specification/) ecosystem. Build secure, discoverable agents that seamlessly integrate with the growing A2A network.

## Quick Start

### 1. Install Phlow

```bash
# JavaScript/TypeScript
npm install phlow-auth

# Python
pip install phlow-auth

# CLI Tools (optional)
npm install -g phlow-cli
```

### 2. Setup Agent Registry

1. Create a Supabase project at [supabase.com](https://supabase.com)
2. Run the [A2A-compatible agent registry schema](database-schema.sql):

```sql
CREATE TABLE agent_cards (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  agent_id TEXT UNIQUE NOT NULL,
  name TEXT NOT NULL,
  description TEXT,
  public_key TEXT NOT NULL,
  -- A2A Protocol fields
  schema_version TEXT DEFAULT '0.1.0',
  service_url TEXT,
  skills JSONB DEFAULT '[]',
  security_schemes JSONB DEFAULT '{"phlow-jwt": {"type": "http", "scheme": "bearer"}}',
  metadata JSONB DEFAULT '{}',
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

3. Get your credentials from Settings → API

### 3. Generate RSA Keys

```bash
# Using CLI
phlow-cli generate-keys

# Or using OpenSSL
openssl genrsa -out private.pem 2048
openssl rsa -in private.pem -pubout -out public.pem
```

### 4. Create Your A2A-Compatible Agent

```javascript
import { PhlowMiddleware } from 'phlow-auth';
import express from 'express';

const app = express();
app.use(express.json());

// Initialize with A2A Protocol AgentCard
const phlow = new PhlowMiddleware({
  supabaseUrl: process.env.SUPABASE_URL,
  supabaseAnonKey: process.env.SUPABASE_ANON_KEY,
  agentCard: {
    agentId: 'my-agent',
    name: 'My AI Agent',
    description: 'An example AI agent',
    publicKey: process.env.PUBLIC_KEY,
    serviceUrl: 'https://my-agent.example.com',
    skills: [
      { name: 'chat', description: 'Natural language conversation' },
      { name: 'analyze', description: 'Data analysis' }
    ]
  },
  privateKey: process.env.PRIVATE_KEY
});

// A2A Protocol: Expose agent discovery endpoint
app.get('/.well-known/agent.json', phlow.wellKnownHandler());

// Protected endpoint
app.post('/chat', phlow.authenticate(), (req, res) => {
  const { message } = req.body;
  const { agent, claims } = req.phlow;
  
  res.json({
    reply: `Hello from ${agent.name}!`,
    skills: claims.skills
  });
});

app.listen(3000);
```

### 5. Test A2A Agent Discovery

Verify your agent follows A2A Protocol discovery standards:

```bash
# View your agent's capabilities
curl http://localhost:3000/.well-known/agent.json

# Expected A2A Protocol AgentCard response:
{
  "schemaVersion": "0.1.0",
  "name": "My AI Agent",
  "description": "An example AI agent",
  "serviceUrl": "https://my-agent.example.com",
  "skills": [
    { "name": "chat", "description": "Natural language conversation" },
    { "name": "analyze", "description": "Data analysis" }
  ],
  "securitySchemes": {
    "phlow-jwt": {
      "type": "http",
      "scheme": "bearer",
      "bearerFormat": "JWT"
    }
  }
}
```

### 6. Test Authentication

```bash
# Generate a test token (using another agent's credentials)
npx phlow-cli test-token --target my-agent

# Use the token to call your agent
curl -X POST http://localhost:3000/chat \
  -H "Authorization: Bearer <jwt-token>" \
  -H "X-Phlow-Agent-Id: test-agent" \
  -H "Content-Type: application/json" \
  -d '{"message": "Hello!"}'
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
from phlow.integrations.fastapi import create_phlow_dependency

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
from phlow import generate_token

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

### A2A Protocol AgentCards
AgentCards follow the A2A Protocol specification and contain identity, capabilities, and permission information:

```javascript
// A2A Protocol-compatible AgentCard
const agentCard = {
  agentId: 'unique-agent-identifier',
  name: 'Human-readable name',
  description: 'Optional description',
  publicKey: 'RSA public key in PEM format',
  serviceUrl: 'https://agent-url.com',
  skills: [
    { name: 'chat', description: 'Natural language conversation' },
    { name: 'analyze', description: 'Data analysis capabilities' }
  ],
  securitySchemes: {
    'phlow-jwt': {
      type: 'http',
      scheme: 'bearer',
      bearerFormat: 'JWT'
    }
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

- 📖 Read the [API Reference](api-reference.md)
- 🔍 Explore [Examples](examples/basic-agent.md)
- 🧪 Run Integration Tests (see GitHub repository)
- 💬 Join [Discussions](https://github.com/prassanna-ravishankar/phlow/discussions)

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
logging.getLogger('phlow').setLevel(logging.DEBUG)
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