<div align="center">
  <img src="docs/phlow-logo.png" alt="Phlow Logo" width="400">
  
  # Phlow
  
  **JWT authentication middleware for AI agents with Supabase integration**
</div>

<div align="center">

[![npm version](https://img.shields.io/npm/v/phlow-auth.svg)](https://www.npmjs.com/package/phlow-auth)
[![PyPI version](https://img.shields.io/pypi/v/phlow-auth.svg)](https://pypi.org/project/phlow-auth/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

</div>

## 🎯 What is Phlow?

Phlow is authentication middleware for AI agents that's evolving into the **Agent Marketplace Platform** - enabling agents to discover, authenticate, and monetize their capabilities.

**Current: A2A Protocol + Supabase • JWT Auth • Middleware**  
**Vision: The "App Store for AI Agents"**

### 🌟 Our Evolution Path

```
Phase 1: Authentication Middleware (Current)
   ↓
Phase 2: Agent Discovery & Registry  
   ↓
Phase 3: Agent Marketplace Platform
```

We're building the foundational trust layer that will enable agents to securely discover, interact with, and monetize their capabilities - creating the first true marketplace for AI agent services.

## ⚡ Quick Start

```bash
npm install phlow-auth
# or
pip install phlow-auth
```

### JavaScript Example

```javascript
import { PhlowMiddleware } from 'phlow-auth';

const phlow = new PhlowMiddleware({
  agentCard: {
    schemaVersion: '1.0',
    name: 'My Agent',
    description: 'Agent description', 
    serviceUrl: 'https://my-agent.com',
    skills: ['chat', 'analysis'],
    securitySchemes: {},
    metadata: {
      agentId: 'my-agent-id',
      publicKey: 'public-key-here'
    }
  },
  privateKey: process.env.PRIVATE_KEY,
  supabaseUrl: process.env.SUPABASE_URL,
  supabaseAnonKey: process.env.SUPABASE_ANON_KEY
});
```

### Python Example

```python
from phlow_auth import PhlowMiddleware, AgentCard, PhlowConfig

config = PhlowConfig(
    agent_card=AgentCard(
        name="My Agent",
        description="Agent description",
        service_url="https://my-agent.com", 
        skills=["chat", "analysis"],
        metadata={"agent_id": "my-agent-id", "public_key": "public-key-here"}
    ),
    private_key=os.environ["PRIVATE_KEY"],
    supabase_url=os.environ["SUPABASE_URL"],
    supabase_anon_key=os.environ["SUPABASE_ANON_KEY"]
)

phlow = PhlowMiddleware(config)
```

### Express.js Middleware

```javascript
// Use A2A authentication with Supabase features
app.post('/api/chat', phlow.authenticate(), (req, res) => {
  // Access both A2A context and Supabase client
  const { agent, supabase } = req.phlow;
  res.json({ message: `Hello from ${agent.name}` });
});
```

[Full Setup Guide →](docs/getting-started.md)

## 🚀 Features

- **🔐 JWT Authentication** - Verify A2A Protocol JWT tokens
- **📋 Agent Storage** - Store and retrieve agent cards in Supabase
- **🛡️ RLS Helpers** - Generate basic Supabase Row Level Security policies
- **📊 Basic Audit** - Log authentication events to Supabase
- **🌐 Multi-Language** - JavaScript/TypeScript and Python packages
- **🔧 Middleware** - Express and FastAPI integration helpers


## How It Works

```mermaid
sequenceDiagram
    participant A as Agent A
    participant B as Agent B  
    participant S as Supabase Registry
    
    A->>A: Generate JWT with private key
    A->>B: Send request + JWT + Agent ID header
    B->>S: Lookup Agent A's public key
    S->>B: Return AgentCard with public key
    B->>B: Verify JWT signature
    B->>A: Return response
```

## 📦 What's Included

```
phlow/
├── packages/
│   ├── phlow-auth-js/          # JWT auth middleware for JavaScript
│   └── phlow-auth-python/      # JWT auth middleware for Python
└── docs/
    ├── getting-started.md      # Quick setup guide
    ├── a2a-compatibility.md    # A2A Protocol integration
    └── api-reference.md        # API documentation
```

## 🏗️ How It Works

Phlow is a lightweight middleware that connects A2A Protocol JWT authentication with Supabase storage:

1. **JWT Verification** - Validates A2A Protocol tokens
2. **Agent Lookup** - Retrieves agent cards from Supabase
3. **Context Creation** - Provides agent info and Supabase client to your app
4. **Basic Logging** - Optionally logs auth events

See [Getting Started](docs/getting-started.md) for setup instructions.


## 🔧 Setup

1. **Install**: `npm install phlow-auth` or `pip install phlow-auth`
2. **Configure**: Set up Supabase project and environment variables
3. **Initialize**: Register your agent card in Supabase
4. **Authenticate**: Add Phlow middleware to your A2A agent

[Detailed Setup Instructions →](docs/getting-started.md)

## 💡 Example: A2A Agent with Phlow Auth

```javascript
// A2A + Phlow Integration
import { PhlowMiddleware } from 'phlow-auth';

const agentCard = {
  schemaVersion: '1.0',
  name: 'My Agent',
  description: 'A2A-compatible agent',
  serviceUrl: 'https://my-agent.com',
  skills: ['chat', 'analysis'],
  securitySchemes: {},
  metadata: {
    agentId: 'my-agent-id',
    publicKey: process.env.PUBLIC_KEY
  }
};

// Initialize Phlow for authentication
const phlow = new PhlowMiddleware({
  agentCard,
  supabaseUrl: process.env.SUPABASE_URL,
  supabaseAnonKey: process.env.SUPABASE_ANON_KEY,
  privateKey: process.env.PRIVATE_KEY
});

// Add Phlow auth middleware to Express
app.use('/api/a2a', phlow.authenticate());

// Handle A2A messages
app.post('/api/a2a/message', async (req, res) => {
  const { phlow } = req; // Contains agent, supabase, a2aClient
  // Process A2A message using phlow context
  res.json({ status: 'received' });
});
```

## 📚 Documentation

- **[Getting Started](docs/getting-started.md)** - Quick setup guide
- **[A2A Compatibility](docs/a2a-compatibility.md)** - A2A Protocol integration
- **[API Reference](docs/api-reference.md)** - Complete API docs

## 🌐 Language Support

| Language | Package | Framework Support |
|----------|---------|------------------|
| JavaScript/TypeScript | `phlow-auth` | Express.js, Node.js |
| Python | `phlow-auth` | FastAPI, Flask |

## 🚀 Roadmap & Vision

### Phase 1: Authentication Middleware (Current)
- ✅ JWT authentication for A2A Protocol
- ✅ Agent card storage in Supabase  
- ✅ Basic middleware for Express/FastAPI
- 🔄 Enhanced security and testing

### Phase 2: Agent Discovery & Registry (Next 6 months)
- 🎯 Central agent registry with search capabilities
- 🎯 Agent capability matching and discovery
- 🎯 Enhanced agent profiles and metadata
- 🎯 Agent network visualization

### Phase 3: Agent Marketplace Platform (6-18 months)
- 🎯 Agent monetization and billing
- 🎯 Usage analytics and performance metrics
- 🎯 Agent rating and reputation systems
- 🎯 Developer tools and SDK ecosystem

**Our North Star**: Create the first true marketplace where AI agents can discover, authenticate, and monetize their capabilities - making agent-to-agent commerce as simple as an API call.

## Contributing

Pull requests welcome! We're building towards our marketplace vision:

**Current Focus Areas:**
- Authentication middleware improvements
- Supabase integration enhancements  
- Agent registry and discovery features
- Developer experience improvements

**Future Contribution Areas:**
- Agent marketplace features
- Monetization and billing systems
- Analytics and metrics
- Community tools and governance

**Scope**: Please keep contributions focused on authentication, agent registry, discovery, and marketplace features. Communication protocols should be contributed to the [A2A Protocol](https://github.com/a2aproject) directly.

```bash
git clone https://github.com/prassanna-ravishankar/phlow.git
cd phlow
npm install
npm test
```

## License

MIT License - see [LICENSE](LICENSE) file for details.

---

**Built with ❤️ for the A2A ecosystem**

[Get Started](docs/getting-started.md) | [A2A Compatibility](docs/a2a-compatibility.md) | [API Reference](docs/api-reference.md)