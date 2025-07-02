# Local Development Setup

This guide walks you through setting up a complete Phlow development environment, from initial clone to running examples.

## Prerequisites

### Required Software

**Node.js** (v18 or higher):
```bash
# Check version
node --version

# Install via nvm (recommended)
nvm install 18
nvm use 18
```

**Python** (3.8 or higher):
```bash
# Check version
python --version

# Install via pyenv (recommended)
pyenv install 3.11
pyenv global 3.11
```

**Git**:
```bash
git --version
```

### Development Tools

**Recommended Editor**: Visual Studio Code with extensions:
- TypeScript and JavaScript Language Features
- Python extension
- Prettier - Code formatter
- ESLint
- Python Docstring Generator

## Initial Setup

### 1. Clone Repository

```bash
git clone https://github.com/prassanna-ravishankar/phlow.git
cd phlow
```

### 2. Install Dependencies

**Root workspace**:
```bash
npm install
```

This installs dependencies for all packages using npm workspaces.

**Python packages** (if working on Python code):
```bash
cd packages/phlow-auth-python
pip install -e ".[dev]"
```

### 3. Environment Configuration

**Create environment file**:
```bash
cp .env.example .env
```

**Required environment variables**:
```bash
# Supabase configuration
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=your-anon-key

# RSA key pair (generate using CLI)
PUBLIC_KEY="-----BEGIN PUBLIC KEY-----..."
PRIVATE_KEY="-----BEGIN RSA PRIVATE KEY-----..."

# Optional: Development settings
PHLOW_DEBUG=true
PHLOW_LOG_LEVEL=debug
```

### 4. Generate RSA Keys

```bash
# Using the CLI
npx phlow-cli generate-keys

# Or manually with OpenSSL
openssl genrsa -out private_key.pem 2048
openssl rsa -in private_key.pem -pubout -out public_key.pem
```

### 5. Supabase Setup

**Option A: Use Supabase Cloud**
1. Create project at [supabase.com](https://supabase.com)
2. Copy URL and anon key to `.env`
3. Run database schema:

```sql
-- In Supabase SQL editor
CREATE TABLE agent_cards (
  agent_id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  description TEXT,
  public_key TEXT NOT NULL,
  service_url TEXT,
  permissions JSONB DEFAULT '[]',
  skills JSONB DEFAULT '[]',
  security_schemes JSONB DEFAULT '{}',
  endpoints JSONB DEFAULT '{}',
  metadata JSONB DEFAULT '{}',
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Enable RLS
ALTER TABLE agent_cards ENABLE ROW LEVEL SECURITY;

-- Basic RLS policy
CREATE POLICY "Enable read access for all users" ON agent_cards
FOR SELECT USING (true);

CREATE POLICY "Enable insert for authenticated users" ON agent_cards  
FOR INSERT WITH CHECK (true);
```

**Option B: Local Supabase (Docker)**
```bash
# Install Supabase CLI
npm install -g @supabase/cli

# Start local instance
supabase start

# Apply migrations
supabase db reset
```

## Development Workflow

### Build System

**Build all packages**:
```bash
npm run build
```

**Development mode** (watch for changes):
```bash
npm run dev
```

**Build specific package**:
```bash
cd packages/phlow-auth-js
npm run build
```

### Package Development

#### JavaScript/TypeScript

**phlow-auth-js development**:
```bash
cd packages/phlow-auth-js

# Install dependencies
npm install

# Development mode
npm run dev

# Build
npm run build

# Type checking
npm run type-check

# Linting
npm run lint
npm run lint:fix
```

**File structure**:
```typescript
// src/index.ts - Main exports
export { PhlowMiddleware } from './middleware'
export { generateToken, verifyToken } from './jwt'
export * from './types'
export * from './errors'

// src/middleware.ts - Core implementation
export class PhlowMiddleware {
  // Implementation
}
```

#### Python

**phlow-auth-python development**:
```bash
cd packages/phlow-auth-python

# Install in editable mode
pip install -e ".[dev]"

# Type checking
mypy src/

# Linting and formatting
black src/
isort src/
flake8 src/

# Testing
pytest
pytest --cov=src/phlow_auth
```

**Package structure**:
```python
# src/phlow_auth/__init__.py
from .middleware import PhlowMiddleware
from .types import AgentCard, PhlowConfig
from .exceptions import PhlowError, AuthenticationError

__all__ = ["PhlowMiddleware", "AgentCard", "PhlowConfig", "PhlowError"]
```

### Running Examples

#### Basic Agent (JavaScript)

```bash
cd examples/basic-agent

# Install dependencies
npm install

# Set up environment
cp .env.example .env
# Edit .env with your Supabase credentials

# Start the agent
npm start

# Test the agent
npm test
```

**Test the endpoints**:
```bash
# Health check
curl http://localhost:3000/health

# Agent card discovery
curl http://localhost:3000/.well-known/agent.json

# Protected endpoint (requires authentication)
curl -H "Authorization: Bearer <jwt-token>" \
     -H "x-phlow-agent-id: test-agent" \
     http://localhost:3000/api/data
```

#### Python Client (FastAPI)

```bash
cd examples/python-client

# Install dependencies
pip install -r requirements.txt

# Set up environment
cp .env.example .env

# Start the FastAPI server
uvicorn main:app --reload

# Or using Docker
docker-compose up --build
```

**Test the FastAPI endpoints**:
```bash
# API documentation
open http://localhost:8000/docs

# Agent card
curl http://localhost:8000/.well-known/agent.json

# Protected endpoint
curl -H "Authorization: Bearer <jwt-token>" \
     -H "x-phlow-agent-id: test-agent" \
     http://localhost:8000/protected
```

#### Multi-Agent Network

```bash
cd examples/multi-agent-network

# Install dependencies
npm install

# Start all agents
npm run start:all

# Or start individually
npm run start:auth-agent     # Port 3001
npm run start:data-agent     # Port 3002  
npm run start:compute-agent  # Port 3003

# Run network tests
npm run test:network
```

## Testing

### Running Tests

**All tests**:
```bash
npm run test
```

**Package-specific tests**:
```bash
# JavaScript tests
cd packages/phlow-auth-js
npm test

# Python tests  
cd packages/phlow-auth-python
pytest
```

**Integration tests**:
```bash
cd tests
npm test
```

### Writing Tests

**JavaScript/TypeScript with Jest**:
```typescript
// packages/phlow-auth-js/src/__tests__/jwt.test.ts
import { generateToken, verifyToken } from '../jwt'

describe('JWT Operations', () => {
  const privateKey = process.env.TEST_PRIVATE_KEY!
  const publicKey = process.env.TEST_PUBLIC_KEY!

  test('should generate and verify token', () => {
    const claims = {
      sub: 'test-agent',
      iss: 'test-agent',
      aud: 'target-agent'
    }
    
    const token = generateToken(claims, privateKey)
    expect(token).toBeDefined()
    
    const decoded = verifyToken(token, publicKey)
    expect(decoded.sub).toBe('test-agent')
  })
})
```

**Python with pytest**:
```python
# packages/phlow-auth-python/tests/test_jwt.py
import pytest
from phlow_auth.jwt_utils import generate_token, verify_token

@pytest.mark.asyncio
async def test_generate_and_verify_token():
    claims = {
        "sub": "test-agent",
        "iss": "test-agent", 
        "aud": "target-agent"
    }
    
    token = await generate_token(claims, private_key)
    assert token is not None
    
    decoded = await verify_token(token, public_key)
    assert decoded["sub"] == "test-agent"
```

## Debugging

### Debug Configuration

**VS Code launch.json**:
```json
{
  "version": "0.2.0",
  "configurations": [
    {
      "name": "Debug Basic Agent",
      "type": "node",
      "request": "launch",
      "program": "${workspaceFolder}/examples/basic-agent/index.js",
      "env": {
        "NODE_ENV": "development",
        "PHLOW_DEBUG": "true"
      },
      "console": "integratedTerminal"
    },
    {
      "name": "Debug Python Client",
      "type": "python",
      "request": "launch",
      "program": "${workspaceFolder}/examples/python-client/main.py",
      "env": {
        "PYTHONPATH": "${workspaceFolder}/packages/phlow-auth-python/src"
      },
      "console": "integratedTerminal"
    }
  ]
}
```

### Logging

**JavaScript debug logging**:
```typescript
import debug from 'debug'
const log = debug('phlow:middleware')

log('Processing authentication request')
```

**Python debug logging**:
```python
import logging
logging.basicConfig(level=logging.DEBUG)

logger = logging.getLogger('phlow.middleware')
logger.debug('Processing authentication request')
```

### Common Debug Scenarios

**JWT Verification Issues**:
```bash
# Check token structure
echo "<jwt-token>" | base64 -d

# Verify with CLI
phlow test-token --token "<jwt-token>" --public-key-file public_key.pem
```

**Supabase Connection Issues**:
```javascript
// Test Supabase connection
const { createClient } = require('@supabase/supabase-js')
const supabase = createClient(url, key)

supabase.from('agent_cards').select('*').limit(1)
  .then(console.log)
  .catch(console.error)
```

**Network Issues**:
```bash
# Test agent endpoints
curl -v http://localhost:3000/.well-known/agent.json

# Check port availability
lsof -i :3000
```

## Development Scripts

### Useful npm Scripts

```bash
# Development
npm run dev              # Start all packages in dev mode
npm run build            # Build all packages
npm run clean            # Clean all build artifacts

# Code Quality  
npm run lint             # Lint all code
npm run lint:fix         # Fix linting issues
npm run type-check       # TypeScript type checking
npm run format           # Format code with Prettier

# Testing
npm run test             # Run all tests
npm run test:watch       # Run tests in watch mode
npm run test:coverage    # Generate coverage reports

# Examples
npm run start:examples   # Start all examples
npm run test:examples    # Test all examples
```

### Git Hooks

**Pre-commit hooks** (using husky):
```bash
# Install husky
npm install --save-dev husky

# Set up pre-commit hook
npx husky add .husky/pre-commit "npm run lint && npm run type-check"
```

## Troubleshooting

### Common Issues

**1. Build Failures**
```bash
# Clear caches and reinstall
rm -rf node_modules package-lock.json
npm cache clean --force
npm install
```

**2. TypeScript Errors**
```bash
# Regenerate type definitions
npm run build
npm run type-check
```

**3. Python Import Errors**
```bash
# Reinstall in editable mode
pip uninstall phlow-auth
pip install -e "packages/phlow-auth-python[dev]"
```

**4. Supabase Connection Issues**
```bash
# Verify environment variables
echo $SUPABASE_URL
echo $SUPABASE_ANON_KEY

# Test connection
curl "$SUPABASE_URL/rest/v1/agent_cards?select=*&limit=1" \
  -H "apikey: $SUPABASE_ANON_KEY"
```

### Performance Issues

**Slow builds**:
```bash
# Use Turborepo cache
npm run build -- --cache-dir=.turbo

# Parallel builds
npm run build -- --parallel
```

**Memory issues**:
```bash
# Increase Node.js memory
export NODE_OPTIONS="--max-old-space-size=4096"
npm run build
```

### Getting Help

**Debug information**:
```bash
# System info
npm run info

# Package versions
npm list --depth=0

# Environment check
npm run doctor
```

**Useful resources**:
- [Turborepo Docs](https://turbo.build/repo/docs)
- [Supabase Docs](https://supabase.com/docs)
- [JWT.io](https://jwt.io) for token debugging

---

This setup provides a complete development environment for contributing to Phlow. The next step is exploring the [Testing Strategy](testing-strategy.md) for writing comprehensive tests.