# JavaScript API Reference

Complete API reference for the Phlow JavaScript/TypeScript library.

## PhlowMiddleware

### Constructor

```typescript
new PhlowMiddleware(config: PhlowConfig)
```

**Parameters:**
- `config` - Configuration object

**Example:**
```javascript
const phlow = new PhlowMiddleware({
  agentCard: myAgentCard,
  privateKey: process.env.PRIVATE_KEY,
  supabaseUrl: process.env.SUPABASE_URL,
  supabaseAnonKey: process.env.SUPABASE_ANON_KEY
});
```

### Methods

#### authenticate()

```typescript
authenticate(options?: AuthOptions): MiddlewareFunction
```

Creates authentication middleware for Express.js.

**Parameters:**
- `options` - Optional authentication options

**Returns:** Express middleware function

**Example:**
```javascript
app.post('/api/data', phlow.authenticate(), (req, res) => {
  const { agent, supabase } = req.phlow;
  res.json({ message: `Hello ${agent.name}` });
});
```

#### callAgent()

```typescript
callAgent(url: string, data: any, options?: CallOptions): Promise<any>
```

Make authenticated request to another agent.

**Parameters:**
- `url` - Target agent endpoint
- `data` - Request payload
- `options` - Call options (timeout, headers, etc.)

**Example:**
```javascript
const response = await phlow.callAgent('https://other-agent.com/api/analyze', {
  dataset: 'sales-data.csv'
});
```

#### registerAgent()

```typescript
registerAgent(agentCard: AgentCard): Promise<void>
```

Register agent in Supabase registry.

**Example:**
```javascript
await phlow.registerAgent({
  name: 'My Agent',
  skills: ['data-analysis'],
  serviceUrl: 'https://my-agent.com'
});
```

#### generateRLSPolicy()

```typescript
generateRLSPolicy(agentId: string, permissions: string[]): string
```

Generate Row Level Security policy for Supabase.

**Example:**
```javascript
const policy = phlow.generateRLSPolicy('agent-123', ['read', 'write']);
console.log(policy); // SQL policy statement
```

## Types

### PhlowConfig

```typescript
interface PhlowConfig {
  // Required
  agentCard: AgentCard;
  privateKey: string;
  supabaseUrl: string;
  supabaseAnonKey: string;
  
  // Optional
  enableAuditLog?: boolean;
  enableRateLimiting?: boolean;
  rateLimitConfig?: RateLimitConfig;
}
```

### PhlowContext

```typescript
interface PhlowContext {
  agent: AgentCard;
  token: string;
  claims: any;
  supabase: SupabaseClient;
}
```

### AuthOptions

```typescript
interface AuthOptions {
  requiredPermissions?: string[];
  skipPaths?: string[];
  customHeaders?: Record<string, string>;
}
```

### CallOptions

```typescript
interface CallOptions {
  timeout?: number;
  headers?: Record<string, string>;
  permissions?: string[];
  retryCount?: number;
  retryDelay?: number;
}
```

### RateLimitConfig

```typescript
interface RateLimitConfig {
  windowMs: number;
  maxRequests: number;
  keyGenerator?: (req: any) => string;
}
```

## Errors

### PhlowError

Base error class for all Phlow errors.

```typescript
class PhlowError extends Error {
  code: string;
  statusCode: number;
}
```

### AuthenticationError

```typescript
class AuthenticationError extends PhlowError {
  // Thrown when authentication fails
}
```

### ConfigurationError

```typescript
class ConfigurationError extends PhlowError {
  // Thrown when configuration is invalid
}
```

## Express Integration

### Basic Setup

```javascript
import express from 'express';
import { PhlowMiddleware } from 'phlow-auth';

const app = express();
const phlow = new PhlowMiddleware(config);

// Global middleware
app.use(express.json());

// Protected routes
app.post('/api/*', phlow.authenticate());

// Well-known endpoint (A2A Protocol)
app.get('/.well-known/agent.json', phlow.wellKnownHandler());
```

### Custom Error Handling

```javascript
app.use((error, req, res, next) => {
  if (error instanceof AuthenticationError) {
    res.status(401).json({ error: 'Authentication failed' });
  } else if (error instanceof ConfigurationError) {
    res.status(500).json({ error: 'Server configuration error' });
  } else {
    next(error);
  }
});
```

## Examples

### Multi-Permission Check

```javascript
app.post('/api/admin', 
  phlow.authenticate({ 
    requiredPermissions: ['admin', 'write'] 
  }), 
  (req, res) => {
    // Only agents with admin AND write permissions
    res.json({ message: 'Admin access granted' });
  }
);
```

### Custom Rate Limiting

```javascript
const phlow = new PhlowMiddleware({
  // ... config
  enableRateLimiting: true,
  rateLimitConfig: {
    windowMs: 60000,  // 1 minute
    maxRequests: 100,
    keyGenerator: (req) => req.phlow.agent.metadata.agentId
  }
});
```

### Agent Discovery

```javascript
// Find agents with specific skills
const agents = await phlow.findAgents({
  skills: ['data-analysis', 'ml-training'],
  status: 'online'
});

for (const agent of agents) {
  console.log(`${agent.name}: ${agent.serviceUrl}`);
}
```

### Streaming Responses

```javascript
app.post('/api/stream', phlow.authenticate(), async (req, res) => {
  res.setHeader('Content-Type', 'text/event-stream');
  
  // Stream data back to client
  const stream = await processData(req.body);
  stream.pipe(res);
});
```

## Next Steps

- [Python API](python.md) - Python library reference
- [Configuration](configuration.md) - All config options
- [Examples](../examples/basic-agent.md) - Working examples