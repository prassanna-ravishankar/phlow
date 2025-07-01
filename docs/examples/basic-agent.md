# Basic Agent Example

This example demonstrates how to create a simple Phlow agent that can authenticate with other agents in the network.

## Overview

The basic agent example shows:

- How to initialize a Phlow agent
- Setting up JWT authentication
- Handling incoming requests
- Making authenticated requests to other agents

## Installation

First, clone the repository and navigate to the basic agent example:

```bash
git clone https://github.com/prassanna-ravishankar/phlow.git
cd phlow/examples/basic-agent-example
npm install
```

## Configuration

The basic agent requires a few environment variables:

```bash
# Copy the example environment file
cp .env.example .env

# Edit the environment variables
nano .env
```

Required environment variables:

```env
AGENT_ID=my-basic-agent
AGENT_PORT=3001
SUPABASE_URL=your-supabase-url
SUPABASE_ANON_KEY=your-supabase-anon-key
PRIVATE_KEY_PATH=./keys/private.pem
PUBLIC_KEY_PATH=./keys/public.pem
```

## Generate Keys

Use the Phlow CLI to generate RSA key pairs:

```bash
npx phlow-cli generate-keys --output ./keys
```

## Code Structure

### Main Application (`src/index.js`)

```javascript
const { PhlowAuth } = require('phlow-auth-js');
const express = require('express');

const app = express();
app.use(express.json());

// Initialize Phlow authentication
const phlow = new PhlowAuth({
  agentId: process.env.AGENT_ID,
  privateKeyPath: process.env.PRIVATE_KEY_PATH,
  publicKeyPath: process.env.PUBLIC_KEY_PATH,
  supabaseUrl: process.env.SUPABASE_URL,
  supabaseKey: process.env.SUPABASE_ANON_KEY
});

// Protected route that requires authentication
app.get('/protected', phlow.middleware, (req, res) => {
  res.json({
    message: 'Hello from authenticated agent!',
    caller: req.phlow.agentId,
    timestamp: new Date().toISOString()
  });
});

// Health check endpoint
app.get('/health', (req, res) => {
  res.json({ status: 'healthy', agent: process.env.AGENT_ID });
});

const PORT = process.env.AGENT_PORT || 3001;
app.listen(PORT, () => {
  console.log(`Agent ${process.env.AGENT_ID} running on port ${PORT}`);
});
```

### Making Authenticated Requests

```javascript
// Example of calling another agent
async function callOtherAgent() {
  try {
    const response = await phlow.makeRequest({
      targetAgent: 'other-agent-id',
      endpoint: '/protected',
      method: 'GET'
    });
    
    console.log('Response from other agent:', response.data);
  } catch (error) {
    console.error('Failed to call other agent:', error.message);
  }
}
```

## Running the Example

1. **Start the agent**:
   ```bash
   npm start
   ```

2. **Test authentication**:
   ```bash
   # Test health endpoint (no auth required)
   curl http://localhost:3001/health
   
   # Test protected endpoint with Phlow CLI
   npx phlow-cli test-token --target my-basic-agent --endpoint /protected
   ```

3. **Register with other agents**:
   ```bash
   # Register this agent in the Phlow registry
   npx phlow-cli register-agent --id my-basic-agent --url http://localhost:3001
   ```

## Key Features Demonstrated

### Authentication Middleware

The `phlow.middleware` automatically:
- Validates JWT tokens
- Verifies agent signatures
- Populates `req.phlow` with agent information
- Handles authentication errors

### Secure Communication

All requests between agents are:
- Signed with RSA private keys
- Verified using public keys
- Protected against replay attacks
- Logged for audit purposes

### Error Handling

The example includes comprehensive error handling for:
- Invalid tokens
- Network failures
- Agent not found
- Permission denied

## Next Steps

- [Multi-Agent Network Example](multi-agent.md) - Learn about agent networks
- [API Reference](../api-reference.md) - Complete API documentation
- [Getting Started Guide](../getting-started.md) - Detailed setup instructions

## Troubleshooting

### Common Issues

1. **Agent not found**: Ensure the agent is registered in Supabase
2. **Authentication failed**: Check your RSA keys are valid
3. **Network errors**: Verify agent URLs are accessible
4. **Token expired**: Tokens are valid for 1 hour by default

### Debug Mode

Enable debug logging:

```bash
DEBUG=phlow:* npm start
```

This will show detailed logs of authentication flows and requests.