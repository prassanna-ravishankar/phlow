# Phlow Auth JavaScript

JWT authentication middleware for AI agents with Supabase integration.

## Installation

```bash
npm install phlow-auth
```

## Quick Start

```javascript
import { PhlowMiddleware } from 'phlow-auth';

// Configure your agent
const phlow = new PhlowMiddleware({
  agentCard: {
    schemaVersion: '1.0',
    name: 'My Agent',
    description: 'AI assistant agent',
    serviceUrl: 'https://my-agent.com',
    skills: ['chat', 'analysis'],
    securitySchemes: {},
    metadata: {
      agentId: 'my-agent-id',
      publicKey: 'your-public-key'
    }
  },
  privateKey: process.env.PRIVATE_KEY,
  supabaseUrl: process.env.SUPABASE_URL,
  supabaseAnonKey: process.env.SUPABASE_ANON_KEY
});

// Use with Express
app.post('/api/chat', phlow.authenticate(), (req, res) => {
  const { agent, supabase } = req.phlow;
  res.json({ message: `Hello from ${agent.name}` });
});
```

## Features

- **JWT Authentication** - Verify A2A Protocol JWT tokens
- **Agent Storage** - Store and retrieve agent cards from Supabase
- **RLS Helpers** - Generate basic Row Level Security policies
- **Event Logging** - Track authentication events
- **Express Integration** - Drop-in middleware for Express apps

## Development

```bash
# Clone the repository
git clone https://github.com/prassanna-ravishankar/phlow.git
cd phlow/packages/phlow-auth-js

# Install dependencies
npm install

# Run tests
npm test

# Build
npm run build

# Type checking
npm run typecheck

# Linting
npm run lint
```

## Documentation

- 📖 Documentation: https://prassanna.io/phlow/
- 🐛 Issues: https://github.com/prassanna-ravishankar/phlow/issues
- 💬 Discussions: https://github.com/prassanna-ravishankar/phlow/discussions

## License

MIT License - see LICENSE file for details.