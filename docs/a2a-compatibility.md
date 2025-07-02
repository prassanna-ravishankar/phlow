# A2A Protocol Compatibility

Phlow is designed to evolve toward full compatibility with the [Agent2Agent (A2A) Protocol](https://a2aproject.github.io/A2A/latest/specification/), which provides a comprehensive standard for agent-to-agent communication.

## What is A2A?

The Agent2Agent Protocol is an open standard that enables:

- **Interoperability**: Agents built on different platforms can communicate
- **Task Delegation**: Agents can delegate subtasks to specialized agents  
- **Secure Communication**: Agents exchange information without sharing internal state
- **Discovery**: Agents can find and learn about each other's capabilities

## Current Phlow vs A2A Specification

| Feature | Phlow (Current) | A2A Protocol | Compatibility Status |
|---------|----------------|--------------|---------------------|
| **Authentication** | JWT with RS256 | Multiple schemes (OAuth, Bearer, API Key) | ✅ Partially compatible |
| **Agent Discovery** | Supabase registry | AgentCard + well-known URIs | 🔄 Needs enhancement |
| **Communication** | REST APIs | JSON-RPC 2.0 over HTTPS | 🔄 Planned |
| **Message Format** | Custom JSON | Structured Parts (text, file, data) | 🔄 Planned |
| **Task Management** | None | Stateful task delegation | 🔄 Planned |
| **Streaming** | None | Server-Sent Events | 🔄 Planned |

## Roadmap to A2A Compatibility

### Phase 1: Enhanced Authentication ✅ (Current)
- JWT-based authentication that aligns with A2A security schemes
- Agent registry for public key distribution
- Basic agent-to-agent communication

### Phase 2: AgentCard Standard 🔄 (In Progress)
```json
{
  "schemaVersion": "0.1.0",
  "name": "My Agent",
  "description": "Phlow-enabled agent",
  "serviceUrl": "https://my-agent.example.com",
  "skills": [
    {
      "name": "data-processing",
      "description": "Process and analyze data"
    }
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

### Phase 3: JSON-RPC Support 🔄 (Planned)
```javascript
// A2A-compatible JSON-RPC request
{
  "jsonrpc": "2.0",
  "method": "messages/send",
  "params": {
    "messages": [
      {
        "role": "user",
        "content": {
          "type": "text",
          "text": "Process this data for me"
        }
      }
    ]
  },
  "id": 1
}
```

### Phase 4: Task Management 🔄 (Planned)
- Stateful task creation and management
- Task delegation between agents
- Progress tracking and cancellation
- Push notifications for task updates

### Phase 5: Full A2A Compliance 🔄 (Future)
- Complete message part support (text, file, structured data)
- Server-Sent Events streaming
- Well-known endpoint discovery
- Enhanced security and credential management

## Migration Path

### For Current Phlow Users

When A2A compatibility is implemented, existing Phlow applications will:

1. **Continue working** with current JWT authentication
2. **Gain new capabilities** through A2A-compatible endpoints
3. **Optionally upgrade** to full A2A compliance when ready

### Example: Adding A2A Support

```javascript
// Current Phlow usage
const phlow = new PhlowMiddleware({ /* config */ });
app.get('/api/data', phlow.authenticate(), handler);

// Future A2A-compatible usage
app.use('/a2a', phlow.a2aHandler()); // Handles JSON-RPC
app.get('/.well-known/agent.json', phlow.agentCard()); // Discovery
```

## Benefits of A2A Compatibility

### 🔗 **Ecosystem Integration**
- Connect with agents built using different frameworks
- Join the broader A2A ecosystem
- Access to A2A-compatible tools and services

### 🚀 **Enhanced Capabilities**
- Task delegation and complex workflows
- Real-time streaming communication
- Standardized agent discovery

### 🔒 **Improved Security**
- Multiple authentication schemes
- Enhanced credential management
- Better security standards compliance

### 📈 **Future-Proofing**
- Alignment with emerging industry standards
- Compatibility with major AI platforms
- Community-driven development

## Community and Standards

The A2A Protocol is:

- **Open Source**: Apache License 2.0
- **Community Driven**: Open to contributions
- **Industry Backed**: Supported by Google and the broader AI community
- **Well Documented**: Comprehensive specification and examples

## Getting Involved

- **Track Progress**: Follow Phlow's A2A compatibility in our GitHub issues
- **Contribute**: Help implement A2A features
- **Test**: Try A2A compatibility as features become available
- **Feedback**: Share your A2A integration needs

---

*Phlow aims to bridge current JWT authentication needs with the future of standardized agent communication through A2A protocol compatibility.*