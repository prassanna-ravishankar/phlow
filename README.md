<div align="center">
  <img src="docs/phlow-logo.png" alt="Phlow Logo" width="400">
  
  # Phlow: A2A Protocol Authentication
  
  *The authentication foundation for the Agent-to-Agent Protocol ecosystem*
</div>

[![npm version](https://img.shields.io/npm/v/phlow-auth.svg)](https://www.npmjs.com/package/phlow-auth)
[![PyPI version](https://img.shields.io/pypi/v/phlow-auth.svg)](https://pypi.org/project/phlow-auth/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## 🎯 What is Phlow?

Phlow is the JWT authentication foundation for the [A2A Protocol](https://a2aproject.github.io/A2A/latest/specification/) ecosystem. It enables AI agents to securely authenticate with each other while maintaining full compatibility with A2A standards for discovery, capabilities, and communication.

**A2A Protocol Native • Secure • Developer-Friendly**

## ⚡ Quick Start

```bash
npm install phlow-auth
```

```javascript
import { PhlowMiddleware } from 'phlow-auth';

const phlow = new PhlowMiddleware({
  supabaseUrl: process.env.SUPABASE_URL,
  supabaseAnonKey: process.env.SUPABASE_ANON_KEY,
  agentCard: {
    agentId: 'my-agent',
    name: 'My Agent',
    description: 'A simple AI agent',
    publicKey: process.env.PUBLIC_KEY,
    serviceUrl: 'https://my-agent.com',
    skills: [
      { name: 'chat', description: 'Natural language chat' },
      { name: 'analyze', description: 'Data analysis' }
    ]
  },
  privateKey: process.env.PRIVATE_KEY
});

// A2A Protocol: Expose agent capabilities
app.get('/.well-known/agent.json', phlow.wellKnownHandler());

// Authenticate agent-to-agent requests
app.post('/api/chat', phlow.authenticate(), (req, res) => {
  res.json({ 
    message: 'Hello from ' + req.phlow.agent.name,
    skills: req.phlow.claims.skills 
  });
});
```

### Python

```bash
pip install phlow-auth
```

```python
from fastapi import FastAPI, Depends
from phlow_auth import PhlowMiddleware, PhlowConfig, AgentCard
from phlow_auth.integrations.fastapi import create_phlow_dependency

# Configure Phlow
config = PhlowConfig(
    supabase_url=os.getenv("SUPABASE_URL"),
    supabase_anon_key=os.getenv("SUPABASE_ANON_KEY"),
    agent_card=AgentCard(
        agent_id="my-agent",
        name="My Agent", 
        permissions=["read:data", "write:data"],
        public_key=os.getenv("AGENT_PUBLIC_KEY"),
    ),
    private_key=os.getenv("AGENT_PRIVATE_KEY"),
)

phlow = PhlowMiddleware(config)
auth_required = create_phlow_dependency(phlow)

@app.get("/protected")
async def protected_endpoint(context = Depends(auth_required)):
    return {"message": "Authenticated!", "agent": context.agent.name}
```

### CLI Tools

```bash
# Install CLI globally
npm install -g phlow-cli

# Initialize new project
phlow init

# Generate and register agent card
phlow generate-card

# Start development environment
phlow dev-start
```

## 🚀 Features

- **🔐 Simple JWT Auth** - RS256 signed tokens, no complexity
- **🤖 A2A Protocol Native** - Full AgentCard and discovery compliance
- **🔍 Well-Known Endpoints** - Standard `/.well-known/agent.json` support
- **🗃️ Supabase Registry** - Store agent public keys and metadata
- **🌐 Multi-Language** - JavaScript/TypeScript and Python
- **🛠️ CLI Tools** - Quick setup and testing

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
│   ├── phlow-auth-js/          # Core JavaScript library
│   ├── phlow-auth-python/      # Core Python library  
│   └── phlow-cli/              # CLI tools
├── examples/
│   └── a2a-compatible-agent/   # A2A Protocol example
└── docs/
    ├── getting-started.md      # Quick setup guide
    ├── a2a-compatibility.md    # A2A Protocol integration
    └── api-reference.md        # API documentation
```

## A2A Protocol Compatibility

Phlow implements key aspects of the [A2A Protocol](https://a2aproject.github.io/A2A/latest/specification/):

### ✅ A2A Protocol Compliance
- **AgentCard Format** - Complete A2A specification compatibility
- **Well-Known Discovery** - Standard `/.well-known/agent.json` endpoint  
- **JWT Security Schemes** - Seamless A2A authentication integration
- **Skills & Capabilities** - Native A2A agent skill declaration

### 🔄 A2A Protocol Roadmap
- **JSON-RPC 2.0 Messages** - Full A2A message format support
- **Task Management** - A2A stateful task operations  
- **Server-Sent Events** - A2A real-time streaming protocol

See [A2A Protocol Integration Guide](docs/a2a-compatibility.md) for complete specifications.

## 🛠️ Example: A2A Protocol Agent

```javascript
// 1. Configure agent with A2A Protocol AgentCard
const agentCard = {
  agentId: 'weather-agent',
  name: 'Weather Information Agent',
  description: 'Provides weather data and forecasts',
  publicKey: process.env.PUBLIC_KEY,
  serviceUrl: 'https://weather-agent.example.com',
  skills: [
    { name: 'current-weather', description: 'Get current weather' },
    { name: 'forecast', description: 'Get weather forecast' }
  ]
};

// 2. Initialize Phlow
const phlow = new PhlowMiddleware({
  supabaseUrl: process.env.SUPABASE_URL,
  supabaseAnonKey: process.env.SUPABASE_ANON_KEY,
  agentCard,
  privateKey: process.env.PRIVATE_KEY
});

// 3. A2A Protocol: Expose AgentCard for discovery
app.get('/.well-known/agent.json', phlow.wellKnownHandler());

// 4. Protect your endpoints
app.post('/weather/current', phlow.authenticate(), async (req, res) => {
  const { location } = req.body;
  const weather = await getWeather(location);
  res.json({ location, weather, agent: 'weather-agent' });
});
```

## 🔧 Setup

### 1. A2A Agent Registry Schema

Use the provided [A2A Protocol agent registry schema](docs/database-schema.sql) in Supabase:

```sql
CREATE TABLE agent_cards (
  agent_id TEXT UNIQUE NOT NULL,
  name TEXT NOT NULL,
  public_key TEXT NOT NULL,
  -- A2A Protocol specification fields
  service_url TEXT,
  skills JSONB DEFAULT '[]',
  security_schemes JSONB,
  metadata JSONB DEFAULT '{}'
);
```

### 2. Environment Variables

```bash
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=your-anon-key
PUBLIC_KEY="-----BEGIN PUBLIC KEY-----..."
PRIVATE_KEY="-----BEGIN RSA PRIVATE KEY-----..."
```

### 3. Generate Keys

```bash
npx phlow-cli generate-keys
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

## Contributing

Pull requests welcome! Focus areas:
- A2A Protocol compatibility improvements
- Additional language libraries
- Documentation and examples

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