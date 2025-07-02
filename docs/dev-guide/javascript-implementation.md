# JavaScript/TypeScript Implementation

This guide provides an in-depth look at the JavaScript/TypeScript implementation of Phlow authentication, covering architecture, key components, and development patterns.

## Package Overview

**Location**: `/packages/phlow-auth-js/`
**Package Name**: `phlow-auth` (npm)
**Language**: TypeScript with strict configuration
**Build Tool**: tsup for fast bundling
**Target**: Node.js 16+ with dual CommonJS/ESM support

## Architecture

### Core Design Patterns

**1. Middleware Pattern**:
```typescript
// Express.js compatible middleware function
type MiddlewareFunction = (req: Request, res: Response, next: NextFunction) => void | Promise<void>

class PhlowMiddleware {
  authenticate(): MiddlewareFunction {
    return async (req, res, next) => {
      // Authentication logic
    }
  }
}
```

**2. Dependency Injection**:
```typescript
constructor(private config: PhlowConfig) {
  this.supabase = createClient(config.supabaseUrl, config.supabaseAnonKey)
  this.validateConfig()
}
```

**3. Promise-based APIs**:
```typescript
async callAgent(url: string, data: any): Promise<any> {
  // Generate token, make request, handle response
}
```

## Core Components

### PhlowMiddleware Class

**File**: `src/middleware.ts`

```typescript
export class PhlowMiddleware {
  private supabase: SupabaseClient
  private config: PhlowConfig
  private supabaseHelpers: SupabaseHelpers

  constructor(config: PhlowConfig) {
    this.config = this.validateConfig(config)
    this.supabase = createClient(config.supabaseUrl, config.supabaseAnonKey)
    this.supabaseHelpers = new SupabaseHelpers(this.supabase)
  }

  // Core authentication middleware
  authenticate(): MiddlewareFunction {
    return async (req: Request, res: Response, next: NextFunction) => {
      try {
        const token = this.extractToken(req)
        const agentId = this.extractAgentId(req)
        
        const agentCard = await this.supabaseHelpers.getAgentCard(agentId)
        if (!agentCard) {
          throw new AuthenticationError('Agent not found')
        }

        const claims = verifyToken(token, agentCard.publicKey)
        this.validateClaims(claims, agentCard)

        // Attach context to request
        req.phlow = {
          agent: agentCard,
          token,
          claims,
          supabase: this.supabase
        }

        next()
      } catch (error) {
        this.handleError(error, res)
      }
    }
  }

  // A2A Protocol discovery endpoint
  wellKnownHandler(): MiddlewareFunction {
    return (req: Request, res: Response) => {
      const agentCard = this.config.agentCard
      res.json({
        schemaVersion: '1.0',
        agentId: agentCard.agentId,
        name: agentCard.name,
        description: agentCard.description,
        serviceUrl: agentCard.serviceUrl,
        publicKey: agentCard.publicKey,
        skills: agentCard.skills || [],
        securitySchemes: {
          bearer: {
            type: 'bearer',
            scheme: 'bearer'
          }
        },
        endpoints: agentCard.endpoints || {},
        metadata: agentCard.metadata || {}
      })
    }
  }

  // Outbound agent calls
  async callAgent(url: string, data: any, options?: CallOptions): Promise<any> {
    const token = generateToken(
      {
        sub: this.config.agentCard.agentId,
        iss: this.config.agentCard.agentId,
        aud: this.extractAgentIdFromUrl(url),
        permissions: this.config.agentCard.permissions || []
      },
      this.config.privateKey,
      options?.expiresIn || '1h'
    )

    const response = await fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`,
        'x-phlow-agent-id': this.config.agentCard.agentId,
        ...options?.headers
      },
      body: JSON.stringify(data)
    })

    if (!response.ok) {
      throw new Error(`Agent call failed: ${response.status} ${response.statusText}`)
    }

    return response.json()
  }
}
```

### JWT Operations

**File**: `src/jwt.ts`

```typescript
interface JWTClaims {
  sub: string      // Subject (agent being authenticated)
  iss: string      // Issuer (agent making request)
  aud: string      // Audience (target agent)
  exp: number      // Expiration timestamp
  iat: number      // Issued at timestamp
  permissions?: string[]
  skills?: string[]
  metadata?: Record<string, any>
}

export function generateToken(
  claims: Omit<JWTClaims, 'exp' | 'iat'>,
  privateKey: string,
  expiresIn: string = '1h'
): string {
  const now = Math.floor(Date.now() / 1000)
  const expiration = now + parseExpiry(expiresIn)

  const fullClaims: JWTClaims = {
    ...claims,
    iat: now,
    exp: expiration
  }

  return jwt.sign(fullClaims, privateKey, { algorithm: 'RS256' })
}

export function verifyToken(token: string, publicKey: string): JWTClaims {
  try {
    return jwt.verify(token, publicKey, { 
      algorithms: ['RS256'],
      complete: false 
    }) as JWTClaims
  } catch (error) {
    if (error instanceof jwt.TokenExpiredError) {
      throw new AuthenticationError('Token expired', 'TOKEN_EXPIRED')
    }
    if (error instanceof jwt.JsonWebTokenError) {
      throw new AuthenticationError('Invalid token', 'TOKEN_INVALID')
    }
    throw new AuthenticationError('Token verification failed', 'TOKEN_VERIFICATION_FAILED')
  }
}

export function decodeToken(token: string): JWTClaims {
  // WARNING: This does not verify the signature!
  return jwt.decode(token) as JWTClaims
}

function parseExpiry(expiresIn: string): number {
  const match = expiresIn.match(/^(\d+)([smhd])$/)
  if (!match) {
    throw new Error(`Invalid expiry format: ${expiresIn}`)
  }

  const value = parseInt(match[1])
  const unit = match[2]

  const multipliers = {
    s: 1,
    m: 60,
    h: 60 * 60,
    d: 24 * 60 * 60
  }

  return value * multipliers[unit as keyof typeof multipliers]
}
```

### Type System

**File**: `src/types.ts`

```typescript
export interface AgentCard {
  agentId: string
  name: string
  description?: string
  publicKey: string
  serviceUrl?: string
  schemaVersion?: string
  skills?: Array<{
    name: string
    description?: string
  }>
  securitySchemes?: Record<string, {
    type: string
    scheme?: string
    in?: string
    name?: string
  }>
  permissions?: string[]
  endpoints?: Record<string, {
    method: string
    path: string
    description?: string
  }>
  metadata?: Record<string, any>
}

export interface PhlowConfig {
  supabaseUrl: string
  supabaseAnonKey: string
  agentCard: AgentCard
  privateKey: string
  tokenExpiry?: string
  debug?: boolean
}

export interface PhlowContext {
  agent: AgentCard
  token: string
  claims: JWTClaims
  supabase: SupabaseClient
}

export interface CallOptions {
  expiresIn?: string
  headers?: Record<string, string>
  timeout?: number
}

// Extend Express Request type
declare global {
  namespace Express {
    interface Request {
      phlow?: PhlowContext
    }
  }
}
```

### Supabase Integration

**File**: `src/supabase-helpers.ts`

```typescript
export class SupabaseHelpers {
  constructor(private supabase: SupabaseClient) {}

  async registerAgentCard(agentCard: AgentCard): Promise<void> {
    const { error } = await this.supabase
      .from('agent_cards')
      .upsert({
        agent_id: agentCard.agentId,
        name: agentCard.name,
        description: agentCard.description,
        public_key: agentCard.publicKey,
        service_url: agentCard.serviceUrl,
        permissions: agentCard.permissions || [],
        skills: agentCard.skills || [],
        security_schemes: agentCard.securitySchemes || {},
        endpoints: agentCard.endpoints || {},
        metadata: agentCard.metadata || {}
      })

    if (error) {
      throw new Error(`Failed to register agent card: ${error.message}`)
    }
  }

  async getAgentCard(agentId: string): Promise<AgentCard | null> {
    const { data, error } = await this.supabase
      .from('agent_cards')
      .select('*')
      .eq('agent_id', agentId)
      .single()

    if (error) {
      if (error.code === 'PGRST116') {
        return null // Agent not found
      }
      throw new Error(`Failed to get agent card: ${error.message}`)
    }

    return {
      agentId: data.agent_id,
      name: data.name,
      description: data.description,
      publicKey: data.public_key,
      serviceUrl: data.service_url,
      permissions: data.permissions,
      skills: data.skills,
      securitySchemes: data.security_schemes,
      endpoints: data.endpoints,
      metadata: data.metadata
    }
  }

  async searchAgents(filter: AgentFilter): Promise<AgentCard[]> {
    let query = this.supabase.from('agent_cards').select('*')

    if (filter.skills?.length) {
      query = query.contains('skills', filter.skills)
    }

    if (filter.permissions?.length) {
      query = query.contains('permissions', filter.permissions)
    }

    if (filter.metadata) {
      Object.entries(filter.metadata).forEach(([key, value]) => {
        query = query.eq(`metadata->${key}`, value)
      })
    }

    const { data, error } = await query

    if (error) {
      throw new Error(`Failed to search agents: ${error.message}`)
    }

    return data.map(this.mapDatabaseToAgentCard)
  }

  // RLS Policy Generation
  static generateRLSPolicy(
    tableName: string,
    policyName: string,
    policyType: 'basic_auth' | 'agent_specific' | 'permission_based'
  ): string {
    const policies = {
      basic_auth: `
        CREATE POLICY "${policyName}" ON ${tableName}
        FOR SELECT USING (
          EXISTS (
            SELECT 1 FROM agent_cards 
            WHERE agent_id = auth.jwt() ->> 'sub'
          )
        );
      `,
      agent_specific: `
        CREATE POLICY "${policyName}" ON ${tableName}
        FOR ALL USING (
          auth.jwt() ->> 'sub' = agent_id
        );
      `,
      permission_based: `
        CREATE POLICY "${policyName}" ON ${tableName}
        FOR SELECT USING (
          auth.jwt() -> 'permissions' ? 'read:${tableName}'
        );
      `
    }

    return policies[policyType].trim()
  }
}
```

### Error Handling

**File**: `src/errors.ts`

```typescript
export class PhlowError extends Error {
  constructor(
    message: string,
    public code: string = 'PHLOW_ERROR',
    public statusCode: number = 500
  ) {
    super(message)
    this.name = 'PhlowError'
  }
}

export class AuthenticationError extends PhlowError {
  constructor(message: string, code: string = 'AUTH_ERROR') {
    super(message, code, 401)
    this.name = 'AuthenticationError'
  }
}

export class ConfigurationError extends PhlowError {
  constructor(message: string, code: string = 'CONFIG_ERROR') {
    super(message, code, 500)
    this.name = 'ConfigurationError'
  }
}

export class TokenError extends PhlowError {
  constructor(message: string, code: string = 'TOKEN_ERROR') {
    super(message, code, 401)
    this.name = 'TokenError'
  }
}

// Error handler middleware
export function errorHandler(
  error: Error,
  req: Request,
  res: Response,
  next: NextFunction
): void {
  if (error instanceof PhlowError) {
    res.status(error.statusCode).json({
      error: {
        message: error.message,
        code: error.code,
        statusCode: error.statusCode
      }
    })
  } else {
    console.error('Unexpected error:', error)
    res.status(500).json({
      error: {
        message: 'Internal server error',
        code: 'INTERNAL_ERROR',
        statusCode: 500
      }
    })
  }
}
```

## Usage Patterns

### Basic Express.js Integration

```typescript
import express from 'express'
import { PhlowMiddleware, errorHandler } from 'phlow-auth'

const app = express()

const phlow = new PhlowMiddleware({
  supabaseUrl: process.env.SUPABASE_URL!,
  supabaseAnonKey: process.env.SUPABASE_ANON_KEY!,
  agentCard: {
    agentId: 'my-agent',
    name: 'My Agent',
    publicKey: process.env.PUBLIC_KEY!,
    permissions: ['read:data', 'write:data']
  },
  privateKey: process.env.PRIVATE_KEY!
})

// A2A discovery endpoint
app.get('/.well-known/agent.json', phlow.wellKnownHandler())

// Protected routes
app.post('/api/data', phlow.authenticate(), (req, res) => {
  const { agent, claims } = req.phlow!
  
  res.json({
    message: 'Data accessed successfully',
    requestedBy: agent.name,
    permissions: claims.permissions
  })
})

// Error handling
app.use(errorHandler)
```

### Advanced Authentication

```typescript
// Custom permission checking
app.post('/admin/users', phlow.authenticate(), (req, res, next) => {
  const { claims } = req.phlow!
  
  if (!claims.permissions?.includes('admin:users')) {
    return res.status(403).json({
      error: 'Insufficient permissions'
    })
  }
  
  next()
}, (req, res) => {
  // Admin-only functionality
})

// Agent-to-agent communication
app.post('/api/analyze', phlow.authenticate(), async (req, res) => {
  try {
    // Call another agent
    const result = await phlow.callAgent(
      'https://analysis-agent.ai/compute',
      { dataset: req.body.dataset }
    )
    
    res.json(result)
  } catch (error) {
    res.status(500).json({ error: error.message })
  }
})
```

## Build Configuration

### TypeScript Configuration

**tsconfig.json**:
```json
{
  "extends": "../../tsconfig.json",
  "compilerOptions": {
    "outDir": "dist",
    "rootDir": "src",
    "declaration": true,
    "declarationMap": true,
    "sourceMap": true
  },
  "include": ["src/**/*"],
  "exclude": ["node_modules", "dist", "**/*.test.ts"]
}
```

### Build Setup (tsup)

**tsup.config.ts**:
```typescript
import { defineConfig } from 'tsup'

export default defineConfig({
  entry: ['src/index.ts'],
  format: ['cjs', 'esm'],
  dts: true,
  sourcemap: true,
  clean: true,
  external: ['@supabase/supabase-js', 'jsonwebtoken'],
  esbuildOptions: {
    target: 'node16'
  }
})
```

### Package.json Configuration

```json
{
  "name": "phlow-auth",
  "version": "1.0.0",
  "main": "dist/index.js",
  "module": "dist/index.mjs",
  "types": "dist/index.d.ts",
  "exports": {
    ".": {
      "import": "./dist/index.mjs",
      "require": "./dist/index.js",
      "types": "./dist/index.d.ts"
    }
  },
  "files": ["dist"],
  "scripts": {
    "build": "tsup",
    "dev": "tsup --watch",
    "type-check": "tsc --noEmit",
    "lint": "eslint src --ext .ts",
    "test": "jest"
  },
  "dependencies": {
    "@supabase/supabase-js": "^2.38.0",
    "jsonwebtoken": "^9.0.2"
  },
  "devDependencies": {
    "@types/jsonwebtoken": "^9.0.3",
    "@types/node": "^20.8.0",
    "typescript": "^5.2.2",
    "tsup": "^7.2.0"
  }
}
```

## Testing Strategy

### Unit Tests Structure

```typescript
// src/__tests__/middleware.test.ts
import { PhlowMiddleware } from '../middleware'
import { generateToken } from '../jwt'

describe('PhlowMiddleware', () => {
  let middleware: PhlowMiddleware
  let mockRequest: Partial<Request>
  let mockResponse: Partial<Response>
  let nextFunction: jest.Mock

  beforeEach(() => {
    middleware = new PhlowMiddleware({
      // Test configuration
    })
    
    mockRequest = {
      headers: {},
      body: {}
    }
    
    mockResponse = {
      json: jest.fn(),
      status: jest.fn().mockReturnThis()
    }
    
    nextFunction = jest.fn()
  })

  describe('authenticate', () => {
    test('should authenticate valid token', async () => {
      const token = generateToken(/* valid claims */, privateKey)
      mockRequest.headers = {
        'authorization': `Bearer ${token}`,
        'x-phlow-agent-id': 'test-agent'
      }

      const authMiddleware = middleware.authenticate()
      await authMiddleware(mockRequest as Request, mockResponse as Response, nextFunction)

      expect(nextFunction).toHaveBeenCalled()
      expect(mockRequest.phlow).toBeDefined()
    })

    test('should reject invalid token', async () => {
      mockRequest.headers = {
        'authorization': 'Bearer invalid-token',
        'x-phlow-agent-id': 'test-agent'
      }

      const authMiddleware = middleware.authenticate()
      await authMiddleware(mockRequest as Request, mockResponse as Response, nextFunction)

      expect(mockResponse.status).toHaveBeenCalledWith(401)
      expect(nextFunction).not.toHaveBeenCalled()
    })
  })
})
```

## Performance Considerations

### Caching Strategy

```typescript
class PhlowMiddleware {
  private agentCardCache = new Map<string, { card: AgentCard; expires: number }>()
  private publicKeyCache = new Map<string, { key: string; expires: number }>()

  private async getAgentCardCached(agentId: string): Promise<AgentCard | null> {
    const cached = this.agentCardCache.get(agentId)
    if (cached && cached.expires > Date.now()) {
      return cached.card
    }

    const card = await this.supabaseHelpers.getAgentCard(agentId)
    if (card) {
      this.agentCardCache.set(agentId, {
        card,
        expires: Date.now() + 5 * 60 * 1000 // 5 minutes
      })
    }

    return card
  }
}
```

### Optimization Tips

1. **Public Key Caching**: Cache public keys to avoid repeated Supabase queries
2. **Connection Pooling**: Use Supabase connection pooling for high-throughput applications
3. **Token Validation**: Cache JWT verification results for short periods
4. **Async Operations**: Use `Promise.all` for parallel operations where possible

## Security Best Practices

### Token Security

```typescript
// Secure token generation with proper expiry
const token = generateToken(claims, privateKey, '15m') // Short-lived tokens

// Token validation with timing attack protection
function constantTimeCompare(a: string, b: string): boolean {
  if (a.length !== b.length) return false
  
  let result = 0
  for (let i = 0; i < a.length; i++) {
    result |= a.charCodeAt(i) ^ b.charCodeAt(i)
  }
  
  return result === 0
}
```

### Key Management

```typescript
// Validate private key format
function validatePrivateKey(key: string): void {
  if (!key.includes('BEGIN RSA PRIVATE KEY') && !key.includes('BEGIN PRIVATE KEY')) {
    throw new ConfigurationError('Invalid private key format')
  }
}

// Secure key storage recommendations
const secureConfig = {
  privateKey: process.env.PRIVATE_KEY!, // From secure environment
  // Never log or expose private keys
}
```

---

This implementation provides a robust, type-safe foundation for A2A authentication in JavaScript/TypeScript applications. The next step is exploring the [Python Implementation](python-implementation.md) to understand the multi-language approach.