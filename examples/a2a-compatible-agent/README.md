# A2A-Compatible Agent Example

This example demonstrates how to build an agent that is compatible with the A2A Protocol specification while using Phlow for JWT authentication.

## Features

- **A2A AgentCard**: Exposes agent capabilities at `/.well-known/agent.json`
- **JWT Authentication**: Secure agent-to-agent communication
- **Skills Declaration**: Declares agent capabilities in A2A format
- **Future-Ready**: Prepared for JSON-RPC 2.0 support

## Setup

1. Install dependencies:
```bash
npm install
```

2. Configure environment:
```bash
cp .env.example .env
# Edit .env with your Supabase credentials and keys
```

3. Generate RSA keys:
```bash
npx phlow-cli generate-keys
```

4. Start the agent:
```bash
npm start
```

## Endpoints

### A2A Protocol Endpoints

- `GET /.well-known/agent.json` - Agent discovery (AgentCard)
- `POST /a2a` - Future JSON-RPC endpoint (authenticated)

### REST Endpoints (Current)

- `GET /health` - Health check (no auth)
- `POST /echo` - Echo service (authenticated)
- `POST /process` - Data processing (authenticated)

## Testing

### 1. Check AgentCard
```bash
curl http://localhost:3000/.well-known/agent.json
```

### 2. Test Authentication
```bash
# Generate a test token
npx phlow-cli test-token --target a2a-example-agent

# Use the token
curl -X POST http://localhost:3000/echo \
  -H "Authorization: Bearer <token>" \
  -H "X-Phlow-Agent-Id: test-agent" \
  -H "Content-Type: application/json" \
  -d '{"message": "Hello A2A!"}'
```

## A2A Compatibility

This agent follows A2A Protocol conventions:

1. **AgentCard Format**: Exposes capabilities in standard format
2. **Well-known URI**: Uses `/.well-known/agent.json` for discovery
3. **Security Schemes**: Declares JWT authentication method
4. **Skills**: Lists agent capabilities
5. **Future JSON-RPC**: Prepared for A2A message format

## Next Steps

As Phlow evolves toward full A2A compatibility:

1. **JSON-RPC Support**: The `/a2a` endpoint will handle JSON-RPC 2.0
2. **Task Management**: Add stateful task handling
3. **Streaming**: Implement Server-Sent Events for real-time updates
4. **Message Parts**: Support text, file, and structured data parts