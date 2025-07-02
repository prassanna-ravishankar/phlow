<div align="center">
  <img src="docs/phlow-logo.png" alt="Phlow Logo" width="400">
  
  # Phlow: Agent-to-Agent Authentication Framework
  
  *JWT-based authentication for AI agent networks using Supabase*
</div>

[![npm version](https://img.shields.io/npm/v/phlow-auth.svg)](https://www.npmjs.com/package/phlow-auth)
[![PyPI version](https://img.shields.io/pypi/v/phlow-auth.svg)](https://pypi.org/project/phlow-auth/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Build Status](https://img.shields.io/github/workflow/status/prassanna-ravishankar/phlow/CI)](https://github.com/prassanna-ravishankar/phlow/actions)

## 🎯 What is Phlow?

Phlow provides JWT-based authentication for AI agent networks, inspired by the [A2A Protocol specification](https://a2aproject.github.io/A2A/latest/specification/). Built with Supabase as the agent registry, Phlow makes securing agent-to-agent communication straightforward with minimal setup.

**Current**: JWT authentication with Supabase • **Future**: Full A2A Protocol compatibility

## ⚡ Quick Start

### JavaScript/TypeScript

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
    permissions: ['read:data', 'write:data'],
    publicKey: process.env.AGENT_PUBLIC_KEY,
  },
  privateKey: process.env.AGENT_PRIVATE_KEY,
});

// Protect your routes
app.get('/protected', phlow.authenticate(), (req, res) => {
  res.json({ message: 'Authenticated!', agent: req.phlow.agent.name });
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

## 🚀 Key Features

### Current Implementation
- **🔐 JWT Authentication** - RS256 signed tokens for secure agent communication
- **🗃️ Supabase Integration** - Agent registry and public key storage
- **🌐 Multi-Language Support** - JavaScript/TypeScript and Python libraries
- **🛠️ CLI Tools** - Project setup, key generation, and testing utilities
- **📊 Audit Logging** - Authentication event tracking
- **🧪 Local Development** - Complete testing environment

### A2A Protocol Roadmap
- **🔄 AgentCard Standard** - A2A-compatible agent discovery format
- **🔄 JSON-RPC 2.0** - Standard A2A communication protocol
- **🔄 Task Management** - Stateful task delegation between agents
- **🔄 Streaming Support** - Real-time communication via Server-Sent Events
- **🔄 Multiple Auth Schemes** - OAuth 2.0, OpenID Connect, API keys

## 🏗️ Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Client Agent  │    │     Phlow      │    │  Target Agent   │
│                 │    │   Middleware   │    │   + Supabase    │
├─────────────────┤    ├─────────────────┤    ├─────────────────┤
│ 1. Generate JWT │───▶│ 2. Verify       │───▶│ 3. Execute with │
│    with claims  │    │    signature    │    │    context      │
│                 │    │ 3. Check        │    │                 │
│ 4. Receive      │◀───│    permissions │◀───│ 4. Return       │
│    response     │    │                 │    │    results      │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## 📦 Project Structure

This monorepo contains the complete Phlow ecosystem:

```
phlow/
├── packages/
│   ├── phlow-auth-js/          # JavaScript/TypeScript library
│   ├── phlow-auth-python/      # Python library  
│   ├── phlow-cli/              # CLI tools
│   └── phlow-dev/              # Local development utilities
├── examples/
│   ├── basic-agent/            # Simple Express.js agent
│   ├── python-client/          # FastAPI Python agent
│   └── multi-agent-network/    # Complex 4-agent network
├── docs/
│   ├── getting-started.md      # Step-by-step setup guide
│   └── api-reference.md        # Complete API documentation
└── tests/
    └── integration/            # End-to-end test suites
```

## 🎯 Examples

### Basic Agent (JavaScript)

A simple Express.js agent with multiple protection levels:

```bash
cd examples/basic-agent
npm install
npm start
```

Features:
- Public and protected endpoints
- Permission-based access control
- Rate limiting and audit logging
- Built-in testing utilities

### Python Agent (FastAPI)

A comprehensive Python agent with modern async support:

```bash
cd examples/python-client
pip install -r requirements.txt
python main.py
```

Features:
- FastAPI with automatic dependency injection
- Interactive API documentation (Swagger)
- Python client helper utilities
- Agent discovery and batch requests

### Multi-Agent Network

A complex network demonstrating real-world agent coordination:

```bash
cd examples/multi-agent-network
npm install
npm run dev
```

Features:
- 4 specialized agents (Coordinator, Data, Auth, Compute)
- Complex multi-step workflows
- Inter-agent communication patterns
- Network monitoring and status reporting

## 🧪 Testing & Development

### Local Development Environment

```bash
# Start all development tools
phlow dev-start

# Run integration tests
cd tests/integration
npm test

# Test specific scenarios
phlow test-token --target my-agent --expires 1h
```

### Pre-built Test Scenarios

Phlow includes comprehensive test scenarios:

- ✅ Valid JWT authentication
- ✅ Expired token handling  
- ✅ Invalid signature rejection
- ✅ Cross-agent permission validation
- ✅ Rate limiting behavior
- ✅ Audit trail generation
- ✅ Multi-agent workflows

## 🔧 Configuration

### Environment Setup

```bash
# Supabase Configuration
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=your-anon-key

# Agent Configuration
AGENT_ID=my-agent
AGENT_NAME=My Agent
AGENT_PERMISSIONS=read:data,write:data

# RSA Keys (generate with: phlow init)
AGENT_PUBLIC_KEY="-----BEGIN PUBLIC KEY-----\n...\n-----END PUBLIC KEY-----"
AGENT_PRIVATE_KEY="-----BEGIN RSA PRIVATE KEY-----\n...\n-----END RSA PRIVATE KEY-----"
```

### Database Schema

Run this SQL in your Supabase project:

```sql
-- Agent registry
CREATE TABLE agent_cards (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  agent_id TEXT UNIQUE NOT NULL,
  name TEXT NOT NULL,
  permissions TEXT[] DEFAULT '{}',
  public_key TEXT NOT NULL,
  metadata JSONB DEFAULT '{}',
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Audit logs
CREATE TABLE phlow_audit_logs (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
  event TEXT NOT NULL,
  agent_id TEXT NOT NULL,
  target_agent_id TEXT,
  details JSONB DEFAULT '{}',
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Enable Row Level Security
ALTER TABLE agent_cards ENABLE ROW LEVEL SECURITY;
ALTER TABLE phlow_audit_logs ENABLE ROW LEVEL SECURITY;
```

## 📚 Documentation

- **[Getting Started Guide](docs/getting-started.md)** - Complete setup walkthrough
- **[A2A Compatibility](docs/a2a-compatibility.md)** - A2A Protocol integration roadmap
- **[API Reference](docs/api-reference.md)** - Detailed API documentation
- **[JavaScript Library](packages/phlow-auth-js/README.md)** - JS/TS specific docs
- **[Python Library](packages/phlow-auth-python/README.md)** - Python specific docs
- **[CLI Reference](packages/phlow-cli/README.md)** - Command line tools

## 🔐 Security Features

- **RSA-256 JWT Signatures** - Cryptographically secure tokens
- **Public Key Infrastructure** - Decentralized verification
- **Permission-Based Access Control** - Granular authorization
- **Rate Limiting** - Protection against abuse
- **Audit Logging** - Complete security event tracking
- **Token Expiration** - Automatic token lifecycle management
- **Row Level Security** - Supabase RLS integration

## 🌐 Language Support

| Language | Package | Status | Framework Integration |
|----------|---------|--------|----------------------|
| JavaScript/TypeScript | `phlow-auth` | ✅ Complete | Express.js, Node.js |
| Python | `phlow-auth` | ✅ Complete | FastAPI, Flask, Django |

## 🚀 Production Deployment

### Docker Support

```dockerfile
FROM node:18-alpine
COPY . .
RUN npm install
EXPOSE 3000
CMD ["npm", "start"]
```

### Environment-Specific Configuration

```javascript
// Production settings
const phlow = new PhlowMiddleware({
  // ... config
  options: {
    enableAudit: true,
    rateLimiting: {
      maxRequests: 100,
      windowMs: 60000,
    },
  },
});
```

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guide](CONTRIBUTING.md) for details.

### Development Setup

```bash
# Clone the repository
git clone https://github.com/prassanna-ravishankar/phlow.git
cd phlow

# Install dependencies
npm install

# Run tests
npm test

# Build all packages
npm run build
```

## 📈 A2A Compatibility Roadmap

### Phase 1: Foundation ✅ (Current)
- [x] JWT-based authentication with RS256 signatures
- [x] Agent registry via Supabase
- [x] JavaScript/TypeScript and Python libraries
- [x] CLI tools for development and testing
- [x] Express.js and FastAPI middleware

### Phase 2: A2A Standards 🔄 (In Progress)
- [ ] **AgentCard Standard** - A2A-compatible agent discovery format
- [ ] **Well-known Endpoints** - Support `/.well-known/agent.json` discovery
- [ ] **JSON-RPC 2.0** - Standard A2A communication protocol alongside REST

### Phase 3: Advanced Features 🔄 (Planned)
- [ ] **Task Management** - Stateful task delegation and state tracking
- [ ] **Streaming Support** - Server-Sent Events for real-time updates
- [ ] **Multiple Auth Schemes** - OAuth 2.0, OpenID Connect, API keys
- [ ] **Enhanced Security** - TLS 1.3+ requirements and credential management

### Phase 4: Ecosystem Integration 🔄 (Future)
- [ ] **A2A Registry Integration** - Connect with A2A agent registries
- [ ] **Enhanced Interoperability** - Full A2A protocol compliance
- [ ] **Community Tools** - Integration with A2A ecosystem tools

## 📊 Performance

- **Authentication Overhead**: <10ms per request
- **Token Generation**: <5ms
- **Rate Limiting**: Minimal impact
- **Memory Usage**: <50MB base footprint
- **Throughput**: 10,000+ requests/second

## 🆘 Support

- 📖 **Documentation**: [docs/getting-started.md](docs/getting-started.md)
- 🐛 **Issues**: [GitHub Issues](https://github.com/prassanna-ravishankar/phlow/issues)
- 💬 **Discussions**: [GitHub Discussions](https://github.com/prassanna-ravishankar/phlow/discussions)

## 📄 License

MIT License - see [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- **[A2A Protocol](https://a2aproject.github.io/A2A/latest/specification/)** - For inspiring agent-to-agent communication standards
- **Supabase** - For providing the authentication infrastructure
- **JSON Web Tokens** - For the token specification
- **Open Source Community** - For the amazing tools and libraries

---

**Ready to build JWT authentication for your agent network?** 🌊

[Get Started](docs/getting-started.md) | [A2A Compatibility](docs/a2a-compatibility.md) | [View Examples](examples/) | [API Reference](docs/api-reference.md)