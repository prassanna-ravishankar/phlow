# Configuration

Configure Phlow for your agent's needs.

## Basic Configuration

### JavaScript
```javascript
const phlow = new PhlowMiddleware({
  // Required
  agentCard: agentCard,           // A2A Protocol agent card
  privateKey: privateKey,         // RSA private key
  supabaseUrl: supabaseUrl,       // Your Supabase project URL
  supabaseAnonKey: supabaseKey,   // Your Supabase anon key
  
  // Optional
  enableAuditLog: true,           // Track auth events (default: false)
  enableRateLimiting: true,       // Enable rate limits (default: false)
  rateLimitConfig: {
    windowMs: 60000,              // Time window (1 minute)
    maxRequests: 100              // Max requests per window
  }
});
```

### Python
```python
phlow = PhlowMiddleware({
    # Required
    'agent_card': agent_card,      # A2A Protocol agent card
    'private_key': private_key,    # RSA private key
    'supabase_url': supabase_url,  # Your Supabase project URL
    'supabase_anon_key': supabase_key,  # Your Supabase anon key
    
    # Optional
    'enable_audit': True,          # Track auth events (default: False)
    'rate_limiting': {
        'max_requests': 100,       # Max requests per window
        'window_ms': 60000         # Time window (1 minute)
    }
})
```

## Agent Card Format

Your agent card must follow the A2A Protocol standard:

```javascript
const agentCard = {
  schemaVersion: '1.0',
  name: 'My Agent',
  description: 'What your agent does',
  serviceUrl: 'https://your-agent.com',
  skills: [
    {
      name: 'skill-name',
      description: 'What this skill does'
    }
  ],
  securitySchemes: {
    'bearer-jwt': {
      type: 'http',
      scheme: 'bearer',
      bearerFormat: 'JWT'
    }
  },
  metadata: {
    agentId: 'unique-agent-id',
    publicKey: 'your-public-key'
  }
};
```

## Environment Variables

### Required Variables
```bash
# Your agent's keys
PHLOW_PRIVATE_KEY="-----BEGIN PRIVATE KEY-----..."
PHLOW_PUBLIC_KEY="-----BEGIN PUBLIC KEY-----..."

# Supabase connection
SUPABASE_URL="https://your-project.supabase.co"
SUPABASE_ANON_KEY="your-anon-key"
```

### Optional Variables
```bash
# Enable features
PHLOW_ENABLE_AUDIT=true
PHLOW_ENABLE_RATE_LIMIT=true

# Rate limiting
PHLOW_RATE_LIMIT_WINDOW_MS=60000
PHLOW_RATE_LIMIT_MAX_REQUESTS=100

# Agent info
PHLOW_AGENT_ID="my-agent-001"
PHLOW_AGENT_NAME="My Agent"
PHLOW_SERVICE_URL="https://my-agent.com"
```

## Loading Configuration

### From Environment
```javascript
const phlow = new PhlowMiddleware({
  agentCard: {
    name: process.env.PHLOW_AGENT_NAME,
    metadata: {
      agentId: process.env.PHLOW_AGENT_ID,
      publicKey: process.env.PHLOW_PUBLIC_KEY
    }
    // ... other fields
  },
  privateKey: process.env.PHLOW_PRIVATE_KEY,
  supabaseUrl: process.env.SUPABASE_URL,
  supabaseAnonKey: process.env.SUPABASE_ANON_KEY
});
```

### From Config File
```javascript
// config.json
{
  "agentCard": { /* ... */ },
  "supabase": {
    "url": "...",
    "anonKey": "..."
  }
}

// Load it
const config = require('./config.json');
const phlow = new PhlowMiddleware(config);
```

## Security Configuration

### Key Generation
```bash
# Generate new RSA key pair
phlow generate-keys

# Output:
# Private key saved to: private_key.pem
# Public key saved to: public_key.pem
```

### Key Storage Best Practices
- Never commit private keys to git
- Use environment variables or secure vaults
- Rotate keys periodically
- Use different keys for each environment

## Advanced Options

### Custom Token Expiry
```javascript
{
  tokenExpiry: '24h',  // Default: '1h'
  refreshThreshold: 600  // Seconds before expiry to refresh
}
```

### Custom Supabase Tables
```javascript
{
  tables: {
    agentCards: 'custom_agents_table',
    auditLogs: 'custom_audit_table'
  }
}
```

### Middleware Options
```javascript
{
  skipPaths: ['/health', '/metrics'],  // Skip auth for these
  customHeaders: {
    agentId: 'x-custom-agent-id'  // Custom header name
  }
}
```

## Next Steps

- [Authentication Guide](guides/authentication.md) - How auth works
- [Security Best Practices](guides/security.md) - Secure your agent
- [API Reference](api/javascript.md) - All configuration options