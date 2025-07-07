# A2A Protocol Integration

How Phlow leverages the official A2A Protocol SDK.

## What is A2A Protocol?

The [Agent-to-Agent (A2A) Protocol](https://github.com/a2aproject/a2a-js) is an open standard for AI agent communication. It defines:

- **Agent Discovery** - How agents find each other
- **Authentication** - Secure JWT-based identity verification  
- **Messaging** - JSON-RPC 2.0 communication protocol
- **Task Management** - Stateful operation handling

## Phlow's A2A Foundation

Phlow extends the official A2A SDK instead of reimplementing it:

```javascript
import { A2AServer } from '@a2a-js/sdk';

class PhlowMiddleware extends A2AServer {
  // Phlow adds Supabase features to A2A
}
```

### What A2A SDK Provides

| Feature | Description |
|---------|-------------|
| **AgentCard** | Standard metadata format |
| **JWT Auth** | RS256 token validation |
| **Well-Known Endpoints** | `/.well-known/agent.json` |
| **JSON-RPC** | Request/response handling |
| **Task Management** | Async operations |
| **Error Handling** | Standard error codes |

### What Phlow Adds

| Feature | Description |
|---------|-------------|
| **Audit Logging** | Track all auth events |
| **Agent Registry** | Centralized discovery |
| **Rate Limiting** | Request throttling |
| **RLS Policies** | Database security |
| **Multi-Framework** | Express, FastAPI, etc. |

## A2A Compliance

Phlow maintains full A2A Protocol compliance:

### ✅ Agent Card Format
```javascript
{
  "schemaVersion": "1.0",
  "name": "My Agent",
  "description": "What the agent does",
  "serviceUrl": "https://my-agent.com",
  "skills": [
    { "name": "data-analysis", "description": "..." }
  ],
  "securitySchemes": {
    "bearer-jwt": {
      "type": "http",
      "scheme": "bearer",
      "bearerFormat": "JWT"
    }
  }
}
```

### ✅ JWT Token Structure
```javascript
{
  "sub": "target-agent-id",
  "iss": "source-agent-id", 
  "aud": "target-agent-id",
  "exp": 1234567890,
  "iat": 1234567890,
  "permissions": ["read", "write"]
}
```

### ✅ Well-Known Discovery
```bash
GET /.well-known/agent.json
# Returns standard A2A agent card
```

### ✅ JSON-RPC Messages
```javascript
// A2A standard message format
{
  "jsonrpc": "2.0",
  "id": "123",
  "method": "sendMessage",
  "params": {
    "message": "Hello from Agent A"
  }
}
```

## Integration Benefits

### 🔄 **Future-Proof**
- Automatic A2A protocol updates
- No custom maintenance required
- Community-driven development

### 🛡️ **Security**  
- Battle-tested A2A authentication
- Standard JWT implementation
- Peer-reviewed security model

### 🤝 **Interoperability**
- Works with any A2A agent
- Standard discovery mechanisms
- Compatible with A2A ecosystem

### 📈 **Ecosystem**
- Access to A2A community
- Shared tooling and libraries
- Standard best practices

## Migration from Custom Auth

If you're using custom authentication, Phlow makes A2A adoption simple:

### Before (Custom Auth)
```javascript
// Custom token validation
const token = extractToken(req);
const payload = jwt.verify(token, publicKey);
const agent = await db.agents.findById(payload.agentId);
```

### After (Phlow + A2A)
```javascript
// A2A standard authentication
app.post('/api', phlow.authenticate(), (req, res) => {
  // req.phlow contains validated A2A context
});
```

## A2A SDK Versions

Phlow tracks the latest A2A SDK versions:

| Phlow Version | A2A SDK Version | Features |
|---------------|-----------------|----------|
| 0.1.x | 1.0.x | Basic auth, discovery |
| 0.2.x | 1.1.x | Task management |
| 0.3.x | 1.2.x | Streaming support |

## Contributing to A2A

Since Phlow uses the official A2A SDK, improvements benefit the entire ecosystem:

- [A2A Protocol Spec](https://github.com/a2aproject/a2a-spec)
- [A2A JavaScript SDK](https://github.com/a2aproject/a2a-js)
- [A2A Python SDK](https://github.com/a2aproject/a2a-python)

## Next Steps

- [JWT Tokens](jwt-tokens.md) - Understanding A2A tokens
- [Making Agent Calls](../guides/agent-calls.md) - A2A communication
- [API Reference](../api/javascript.md) - Phlow's A2A extensions