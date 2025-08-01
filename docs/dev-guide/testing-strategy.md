# Testing Strategy

This guide outlines the comprehensive testing approach for Phlow, covering unit tests, integration tests, end-to-end scenarios, and testing best practices across both JavaScript/TypeScript and Python implementations.

## Testing Philosophy

### Principles

1. **Security First** - Authentication and JWT verification must be thoroughly tested
2. **Cross-Language Compatibility** - JS and Python implementations must be interoperable  
3. **Real-World Scenarios** - Tests should reflect actual agent-to-agent communication patterns
4. **Performance Validation** - Rate limiting, caching, and database queries need performance tests
5. **Failure Modes** - Comprehensive error handling and edge case coverage

### Test Pyramid

```
    🔺 E2E Tests (Few)
   🔺🔺 Integration Tests (Some)  
  🔺🔺🔺 Unit Tests (Many)
 🔺🔺🔺🔺 Static Analysis (Most)
```

## Test Structure

### Package-Level Testing

```
packages/
├── phlow-auth-js/
│   ├── src/
│   │   └── __tests__/          # Unit tests
│   ├── tests/
│   │   ├── integration/        # Integration tests
│   │   └── fixtures/          # Test data
│   └── jest.config.js
├── phlow-auth-python/
│   ├── tests/
│   │   ├── unit/              # Unit tests
│   │   ├── integration/       # Integration tests
│   │   └── fixtures/          # Test data
│   └── pytest.ini
└── tests/                     # Cross-package tests
    ├── e2e/                   # End-to-end scenarios
    ├── interop/               # Cross-language tests
    └── performance/           # Load and performance tests
```

## Unit Testing

### JavaScript/TypeScript (Jest)

#### JWT Operations Testing

```typescript
// packages/phlow-auth-js/src/__tests__/jwt.test.ts
import { generateToken, verifyToken, decodeToken } from '../jwt'
import { TokenError } from '../errors'

describe('JWT Operations', () => {
  const privateKey = `-----BEGIN RSA PRIVATE KEY-----
MIIEpAIBAAKCAQEA...
-----END RSA PRIVATE KEY-----`

  const publicKey = `-----BEGIN PUBLIC KEY-----
MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEA...
-----END PUBLIC KEY-----`

  describe('generateToken', () => {
    it('should generate valid JWT token', () => {
      const claims = {
        sub: 'test-agent',
        iss: 'test-agent',
        aud: 'target-agent'
      }
      
      const token = generateToken(claims, privateKey, '1h')
      
      expect(token).toBeDefined()
      expect(typeof token).toBe('string')
      expect(token.split('.')).toHaveLength(3) // JWT format
    })

    it('should include all required claims', () => {
      const claims = {
        sub: 'test-agent',
        iss: 'test-agent',
        aud: 'target-agent',
        permissions: ['read:data']
      }
      
      const token = generateToken(claims, privateKey)
      const decoded = decodeToken(token)
      
      expect(decoded.sub).toBe('test-agent')
      expect(decoded.iss).toBe('test-agent')
      expect(decoded.aud).toBe('target-agent')
      expect(decoded.permissions).toEqual(['read:data'])
      expect(decoded.iat).toBeDefined()
      expect(decoded.exp).toBeDefined()
    })

    it('should parse different expiry formats', () => {
      const testCases = [
        { input: '30s', expected: 30 },
        { input: '15m', expected: 15 * 60 },
        { input: '2h', expected: 2 * 60 * 60 },
        { input: '1d', expected: 24 * 60 * 60 }
      ]

      testCases.forEach(({ input, expected }) => {
        const token = generateToken({ sub: 'test' }, privateKey, input)
        const decoded = decodeToken(token)
        const actualExpiry = decoded.exp - decoded.iat
        expect(actualExpiry).toBe(expected)
      })
    })
  })

  describe('verifyToken', () => {
    it('should verify valid token', () => {
      const claims = { sub: 'test-agent', iss: 'test-agent' }
      const token = generateToken(claims, privateKey)
      
      const verified = verifyToken(token, publicKey)
      
      expect(verified.sub).toBe('test-agent')
      expect(verified.iss).toBe('test-agent')
    })

    it('should reject token with wrong public key', () => {
      const wrongPublicKey = `-----BEGIN PUBLIC KEY-----
MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEA[different key]...
-----END PUBLIC KEY-----`

      const claims = { sub: 'test-agent' }
      const token = generateToken(claims, privateKey)
      
      expect(() => verifyToken(token, wrongPublicKey)).toThrow(TokenError)
    })

    it('should reject expired token', () => {
      const claims = { sub: 'test-agent' }
      const token = generateToken(claims, privateKey, '1s')
      
      // Wait for expiration
      return new Promise(resolve => {
        setTimeout(() => {
          expect(() => verifyToken(token, publicKey)).toThrow(TokenError)
          expect(() => verifyToken(token, publicKey)).toThrow(/expired/i)
          resolve(undefined)
        }, 1100)
      })
    })

    it('should reject malformed token', () => {
      expect(() => verifyToken('invalid.token.format', publicKey)).toThrow(TokenError)
      expect(() => verifyToken('', publicKey)).toThrow(TokenError)
    })
  })
})
```

#### Middleware Testing

```typescript
// packages/phlow-auth-js/src/__tests__/middleware.test.ts
import { Request, Response, NextFunction } from 'express'
import { PhlowMiddleware } from '../middleware'
import { AuthenticationError } from '../errors'
import { SupabaseHelpers } from '../supabase-helpers'

// Mock Supabase
jest.mock('../supabase-helpers')
const MockedSupabaseHelpers = SupabaseHelpers as jest.MockedClass<typeof SupabaseHelpers>

describe('PhlowMiddleware', () => {
  let middleware: PhlowMiddleware
  let mockRequest: Partial<Request>
  let mockResponse: Partial<Response>
  let mockNext: NextFunction
  let mockSupabaseHelpers: jest.Mocked<SupabaseHelpers>

  beforeEach(() => {
    const config = {
      supabaseUrl: 'https://test.supabase.co',
      supabaseAnonKey: 'test-key',
      agentCard: {
        agentId: 'middleware-test',
        name: 'Test Agent',
        publicKey: TEST_PUBLIC_KEY
      },
      privateKey: TEST_PRIVATE_KEY
    }

    middleware = new PhlowMiddleware(config)
    
    // Setup mocks
    mockSupabaseHelpers = {
      getAgentCard: jest.fn(),
      registerAgentCard: jest.fn()
    } as any

    middleware['supabaseHelpers'] = mockSupabaseHelpers

    mockRequest = {
      headers: {},
      body: {}
    }

    mockResponse = {
      json: jest.fn(),
      status: jest.fn().mockReturnThis(),
      send: jest.fn()
    }

    mockNext = jest.fn()
  })

  describe('authenticate()', () => {
    it('should authenticate valid request', async () => {
      // Setup test data
      const agentCard = {
        agentId: 'requesting-agent',
        name: 'Requesting Agent',
        publicKey: TEST_PUBLIC_KEY
      }

      mockSupabaseHelpers.getAgentCard.mockResolvedValue(agentCard)

      const token = generateToken(
        { sub: 'requesting-agent', iss: 'requesting-agent' },
        TEST_PRIVATE_KEY
      )

      mockRequest.headers = {
        'authorization': `Bearer ${token}`,
        'x-phlow-agent-id': 'requesting-agent'
      }

      // Execute middleware
      const authMiddleware = middleware.authenticate()
      await authMiddleware(mockRequest as Request, mockResponse as Response, mockNext)

      // Verify results
      expect(mockNext).toHaveBeenCalled()
      expect(mockRequest.phlow).toBeDefined()
      expect(mockRequest.phlow!.agent.agentId).toBe('requesting-agent')
      expect(mockRequest.phlow!.token).toBe(token)
    })

    it('should reject request without authorization header', async () => {
      mockRequest.headers = {
        'x-phlow-agent-id': 'test-agent'
      }

      const authMiddleware = middleware.authenticate()
      await authMiddleware(mockRequest as Request, mockResponse as Response, mockNext)

      expect(mockResponse.status).toHaveBeenCalledWith(401)
      expect(mockNext).not.toHaveBeenCalled()
    })

    it('should reject request without agent ID header', async () => {
      const token = generateToken({ sub: 'test' }, TEST_PRIVATE_KEY)
      
      mockRequest.headers = {
        'authorization': `Bearer ${token}`
      }

      const authMiddleware = middleware.authenticate()
      await authMiddleware(mockRequest as Request, mockResponse as Response, mockNext)

      expect(mockResponse.status).toHaveBeenCalledWith(400)
      expect(mockNext).not.toHaveBeenCalled()
    })

    it('should reject request for non-existent agent', async () => {
      mockSupabaseHelpers.getAgentCard.mockResolvedValue(null)

      const token = generateToken({ sub: 'unknown-agent' }, TEST_PRIVATE_KEY)
      
      mockRequest.headers = {
        'authorization': `Bearer ${token}`,
        'x-phlow-agent-id': 'unknown-agent'
      }

      const authMiddleware = middleware.authenticate()
      await authMiddleware(mockRequest as Request, mockResponse as Response, mockNext)

      expect(mockResponse.status).toHaveBeenCalledWith(401)
      expect(mockNext).not.toHaveBeenCalled()
    })
  })

  describe('wellKnownHandler()', () => {
    it('should return agent card in A2A format', () => {
      const handler = middleware.wellKnownHandler()
      handler(mockRequest as Request, mockResponse as Response)

      expect(mockResponse.json).toHaveBeenCalledWith(
        expect.objectContaining({
          schemaVersion: '1.0',
          agentId: 'middleware-test',
          name: 'Test Agent',
          publicKey: TEST_PUBLIC_KEY,
          securitySchemes: expect.objectContaining({
            bearer: { type: 'bearer', scheme: 'bearer' }
          })
        })
      )
    })
  })

  describe('callAgent()', () => {
    it('should make authenticated request to other agent', async () => {
      // Mock fetch
      global.fetch = jest.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve({ result: 'success' })
      })

      const response = await middleware.callAgent(
        'https://other-agent.ai/analyze',
        { data: 'test' }
      )

      expect(fetch).toHaveBeenCalledWith(
        'https://other-agent.ai/analyze',
        expect.objectContaining({
          method: 'POST',
          headers: expect.objectContaining({
            'Authorization': expect.stringMatching(/^Bearer /),
            'x-phlow-agent-id': 'middleware-test'
          }),
          body: JSON.stringify({ data: 'test' })
        })
      )

      expect(response).toEqual({ result: 'success' })
    })
  })
})
```

### Python (pytest)

#### JWT Operations Testing

```python
# packages/phlow-auth-python/tests/unit/test_jwt.py
import pytest
import time
from phlow.jwt_utils import generate_token, verify_token, is_token_expired
from phlow.exceptions import TokenError

class TestJWTOperations:
    
    @pytest.fixture
    def key_pair(self):
        return {
            'private_key': """-----BEGIN RSA PRIVATE KEY-----
MIIEpAIBAAKCAQEA...
-----END RSA PRIVATE KEY-----""",
            'public_key': """-----BEGIN PUBLIC KEY-----
MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEA...
-----END PUBLIC KEY-----"""
        }

    @pytest.mark.asyncio
    async def test_generate_token(self, key_pair):
        """Test JWT token generation."""
        claims = {
            'sub': 'test-agent',
            'iss': 'test-agent', 
            'aud': 'target-agent'
        }
        
        token = await generate_token(claims, key_pair['private_key'])
        
        assert token is not None
        assert isinstance(token, str)
        assert len(token.split('.')) == 3  # JWT format

    @pytest.mark.asyncio
    async def test_verify_token(self, key_pair):
        """Test JWT token verification."""
        claims = {
            'sub': 'test-agent',
            'iss': 'test-agent'
        }
        
        token = await generate_token(claims, key_pair['private_key'])
        verified = await verify_token(token, key_pair['public_key'])
        
        assert verified['sub'] == 'test-agent'
        assert verified['iss'] == 'test-agent'
        assert 'iat' in verified
        assert 'exp' in verified

    @pytest.mark.asyncio
    async def test_verify_token_wrong_key(self, key_pair):
        """Test token verification with wrong public key."""
        wrong_key = """-----BEGIN PUBLIC KEY-----
MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEA[different]...
-----END PUBLIC KEY-----"""
        
        claims = {'sub': 'test-agent'}
        token = await generate_token(claims, key_pair['private_key'])
        
        with pytest.raises(TokenError, match="verification failed"):
            await verify_token(token, wrong_key)

    @pytest.mark.asyncio
    async def test_expired_token(self, key_pair):
        """Test expired token handling."""
        claims = {'sub': 'test-agent'}
        token = await generate_token(claims, key_pair['private_key'], '1s')
        
        # Wait for expiration
        await asyncio.sleep(1.1)
        
        with pytest.raises(TokenError, match="expired"):
            await verify_token(token, key_pair['public_key'])

    @pytest.mark.parametrize("expires_in,expected_seconds", [
        ("30s", 30),
        ("15m", 15 * 60),
        ("2h", 2 * 60 * 60),
        ("1d", 24 * 60 * 60)
    ])
    @pytest.mark.asyncio
    async def test_expiry_parsing(self, key_pair, expires_in, expected_seconds):
        """Test different expiry time formats."""
        claims = {'sub': 'test'}
        token = await generate_token(claims, key_pair['private_key'], expires_in)
        
        # Decode without verification to check expiry
        import jwt
        decoded = jwt.decode(token, options={"verify_signature": False})
        actual_expiry = decoded['exp'] - decoded['iat']
        
        assert actual_expiry == expected_seconds

    def test_is_token_expired(self, key_pair):
        """Test token expiration checking."""
        # Create already expired token
        import jwt
        import time
        
        expired_claims = {
            'sub': 'test',
            'exp': int(time.time()) - 3600  # 1 hour ago
        }
        
        expired_token = jwt.encode(expired_claims, key_pair['private_key'], algorithm='RS256')
        
        assert is_token_expired(expired_token) == True
        
        # Create valid token
        valid_claims = {
            'sub': 'test',
            'exp': int(time.time()) + 3600  # 1 hour from now
        }
        
        valid_token = jwt.encode(valid_claims, key_pair['private_key'], algorithm='RS256')
        
        assert is_token_expired(valid_token) == False
```

#### Middleware Testing

```python
# packages/phlow-auth-python/tests/unit/test_middleware.py
import pytest
from unittest.mock import AsyncMock, Mock
from phlow import PhlowMiddleware, PhlowConfig, AgentCard
from phlow.exceptions import AuthenticationError, TokenError

class TestPhlowMiddleware:
    
    @pytest.fixture
    def config(self):
        return PhlowConfig(
            supabase_url="https://test.supabase.co",
            supabase_anon_key="test-key",
            agent_card=AgentCard(
                agent_id="test-middleware",
                name="Test Middleware Agent",
                public_key=TEST_PUBLIC_KEY
            ),
            private_key=TEST_PRIVATE_KEY
        )

    @pytest.fixture
    def middleware(self, config):
        return PhlowMiddleware(config)

    @pytest.mark.asyncio
    async def test_authenticate_success(self, middleware):
        """Test successful authentication."""
        # Mock Supabase helper
        test_agent = AgentCard(
            agent_id="requesting-agent",
            name="Requesting Agent",
            public_key=TEST_PUBLIC_KEY
        )
        
        middleware.supabase_helpers.get_agent_card = AsyncMock(return_value=test_agent)
        
        # Generate valid token
        token = await generate_token(
            {"sub": "requesting-agent", "iss": "requesting-agent"},
            TEST_PRIVATE_KEY
        )
        
        # Test authentication
        context = await middleware.authenticate(token, "requesting-agent")
        
        assert context.agent.agent_id == "requesting-agent"
        assert context.token == token
        assert context.claims["sub"] == "requesting-agent"

    @pytest.mark.asyncio
    async def test_authenticate_agent_not_found(self, middleware):
        """Test authentication with non-existent agent."""
        middleware.supabase_helpers.get_agent_card = AsyncMock(return_value=None)
        
        token = await generate_token({"sub": "unknown-agent"}, TEST_PRIVATE_KEY)
        
        with pytest.raises(AuthenticationError, match="Agent not found"):
            await middleware.authenticate(token, "unknown-agent")

    @pytest.mark.asyncio
    async def test_authenticate_invalid_token(self, middleware):
        """Test authentication with invalid token."""
        test_agent = AgentCard(
            agent_id="test-agent",
            name="Test Agent",
            public_key=TEST_PUBLIC_KEY
        )
        
        middleware.supabase_helpers.get_agent_card = AsyncMock(return_value=test_agent)
        
        with pytest.raises(TokenError):
            await middleware.authenticate("invalid-token", "test-agent")

    @pytest.mark.asyncio
    async def test_rate_limiting(self, middleware):
        """Test rate limiting functionality."""
        from phlow.rate_limiter import RateLimiter
        
        middleware.rate_limiter = RateLimiter(max_requests=1, window_seconds=60)
        
        # First request should succeed
        await middleware.rate_limiter.check_rate_limit("test-agent")
        
        # Second request should fail
        with pytest.raises(RateLimitError):
            await middleware.rate_limiter.check_rate_limit("test-agent")

    def test_well_known_handler(self, middleware):
        """Test A2A discovery endpoint."""
        response = middleware.well_known_handler()
        
        assert response["schemaVersion"] == "1.0"
        assert response["agentId"] == "test-middleware"
        assert response["name"] == "Test Middleware Agent"
        assert "publicKey" in response
        assert "securitySchemes" in response

    @pytest.mark.asyncio
    async def test_call_agent(self, middleware):
        """Test calling another agent."""
        # Mock HTTP client
        import httpx
        
        mock_response = Mock()
        mock_response.json.return_value = {"result": "success"}
        mock_response.raise_for_status.return_value = None
        
        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        
        with patch('httpx.AsyncClient', return_value=mock_client):
            response = await middleware.call_agent(
                "https://other-agent.ai/analyze",
                {"data": "test"}
            )
        
        assert response == {"result": "success"}
        mock_client.post.assert_called_once()
```

## Integration Testing

### Database Integration

```typescript
// tests/integration/supabase.test.ts
import { createClient } from '@supabase/supabase-js'
import { SupabaseHelpers } from '../../packages/phlow-auth-js/src/supabase-helpers'

describe('Supabase Integration', () => {
  let supabase: SupabaseClient
  let helpers: SupabaseHelpers

  beforeAll(async () => {
    supabase = createClient(
      process.env.TEST_SUPABASE_URL!,
      process.env.TEST_SUPABASE_ANON_KEY!
    )
    helpers = new SupabaseHelpers(supabase)
    
    // Clean test data
    await supabase.from('agent_cards').delete().like('agent_id', 'test-%')
  })

  afterEach(async () => {
    // Clean up after each test
    await supabase.from('agent_cards').delete().like('agent_id', 'test-%')
  })

  describe('Agent Card Management', () => {
    it('should register and retrieve agent card', async () => {
      const agentCard: AgentCard = {
        agentId: 'test-integration-agent',
        name: 'Integration Test Agent',
        description: 'Agent for integration testing',
        publicKey: TEST_PUBLIC_KEY,
        serviceUrl: 'https://test-agent.example.com',
        permissions: ['read:data', 'write:analysis'],
        skills: [
          { name: 'data-analysis', description: 'Analyze data' }
        ],
        metadata: {
          version: '1.0.0',
          environment: 'test'
        }
      }

      // Register agent card
      await helpers.registerAgentCard(agentCard)

      // Retrieve agent card
      const retrieved = await helpers.getAgentCard('test-integration-agent')

      expect(retrieved).toBeDefined()
      expect(retrieved!.agentId).toBe(agentCard.agentId)
      expect(retrieved!.name).toBe(agentCard.name)
      expect(retrieved!.permissions).toEqual(agentCard.permissions)
      expect(retrieved!.skills).toEqual(agentCard.skills)
    })

    it('should search agents by skills', async () => {
      // Register test agents
      const agents = [
        {
          agentId: 'test-data-agent',
          name: 'Data Agent',
          publicKey: TEST_PUBLIC_KEY,
          skills: [{ name: 'data-analysis' }, { name: 'visualization' }]
        },
        {
          agentId: 'test-ml-agent', 
          name: 'ML Agent',
          publicKey: TEST_PUBLIC_KEY,
          skills: [{ name: 'machine-learning' }, { name: 'data-analysis' }]
        }
      ]

      for (const agent of agents) {
        await helpers.registerAgentCard(agent as AgentCard)
      }

      // Search by skill
      const results = await helpers.searchAgents({
        skills: ['data-analysis']
      })

      expect(results).toHaveLength(2)
      expect(results.map(a => a.agentId)).toContain('test-data-agent')
      expect(results.map(a => a.agentId)).toContain('test-ml-agent')
    })

    it('should search agents by permissions', async () => {
      const agentCard: AgentCard = {
        agentId: 'test-admin-agent',
        name: 'Admin Agent',
        publicKey: TEST_PUBLIC_KEY,
        permissions: ['admin:users', 'read:data']
      }

      await helpers.registerAgentCard(agentCard)

      const results = await helpers.searchAgents({
        permissions: ['admin:users']
      })

      expect(results).toHaveLength(1)
      expect(results[0].agentId).toBe('test-admin-agent')
    })
  })

  describe('RLS Policies', () => {
    it('should enforce row level security', async () => {
      // This test would need to be run with different JWT contexts
      // to verify RLS policies are working correctly
      
      // Create agent card with specific permissions
      const agentCard: AgentCard = {
        agentId: 'test-rls-agent',
        name: 'RLS Test Agent',
        publicKey: TEST_PUBLIC_KEY,
        permissions: ['read:public']
      }

      await helpers.registerAgentCard(agentCard)

      // Test would verify that only authorized agents can access this data
      // Implementation depends on test JWT setup
    })
  })
})
```

### Cross-Language Interoperability

```typescript
// tests/interop/js-python-interop.test.ts
import { spawn } from 'child_process'
import { PhlowMiddleware } from '../../packages/phlow-auth-js/src/middleware'

describe('JavaScript-Python Interoperability', () => {
  let jsMiddleware: PhlowMiddleware
  let pythonServer: any

  beforeAll(async () => {
    // Start Python test server
    pythonServer = spawn('python', ['-m', 'tests.fixtures.python_server'], {
      env: { ...process.env, PORT: '3001' }
    })

    // Wait for server to start
    await new Promise(resolve => setTimeout(resolve, 2000))

    // Configure JS middleware
    jsMiddleware = new PhlowMiddleware({
      supabaseUrl: process.env.TEST_SUPABASE_URL!,
      supabaseAnonKey: process.env.TEST_SUPABASE_ANON_KEY!,
      agentCard: {
        agentId: 'js-test-agent',
        name: 'JS Test Agent',
        publicKey: TEST_PUBLIC_KEY
      },
      privateKey: TEST_PRIVATE_KEY
    })
  })

  afterAll(() => {
    pythonServer.kill()
  })

  it('should authenticate JS-generated token in Python', async () => {
    // JS generates token
    const token = generateToken(
      {
        sub: 'js-test-agent',
        iss: 'js-test-agent',
        aud: 'python-test-agent'
      },
      TEST_PRIVATE_KEY
    )

    // Send to Python server
    const response = await fetch('http://localhost:3001/verify-token', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`,
        'x-phlow-agent-id': 'js-test-agent'
      },
      body: JSON.stringify({ data: 'test' })
    })

    expect(response.ok).toBe(true)
    const result = await response.json()
    expect(result.authenticated).toBe(true)
    expect(result.agent_id).toBe('js-test-agent')
  })

  it('should make JS call to Python agent', async () => {
    const response = await jsMiddleware.callAgent(
      'http://localhost:3001/process',
      { dataset: 'test-data.csv' }
    )

    expect(response).toBeDefined()
    expect(response.status).toBe('processed')
  })
})
```

## End-to-End Testing

### Multi-Agent Scenarios

```typescript
// tests/e2e/multi-agent-workflow.test.ts
describe('Multi-Agent Workflow', () => {
  let agents: {
    coordinator: PhlowMiddleware
    dataAgent: PhlowMiddleware  
    analysisAgent: PhlowMiddleware
    reportAgent: PhlowMiddleware
  }

  beforeAll(async () => {
    // Initialize multiple agents
    agents = await setupTestAgents([
      'coordinator-agent',
      'data-agent', 
      'analysis-agent',
      'report-agent'
    ])
  })

  it('should complete full data analysis workflow', async () => {
    // 1. Coordinator requests data collection
    const dataResponse = await agents.coordinator.callAgent(
      'http://localhost:3002/collect',
      { source: 'sales-database', query: 'last-30-days' }
    )

    expect(dataResponse.status).toBe('collected')
    const datasetId = dataResponse.dataset_id

    // 2. Coordinator requests analysis
    const analysisResponse = await agents.coordinator.callAgent(
      'http://localhost:3003/analyze',
      { dataset_id: datasetId, analysis_type: 'trend-analysis' }
    )

    expect(analysisResponse.status).toBe('analyzed')
    const analysisId = analysisResponse.analysis_id

    // 3. Coordinator requests report generation
    const reportResponse = await agents.coordinator.callAgent(
      'http://localhost:3004/generate-report',
      { analysis_id: analysisId, format: 'pdf' }
    )

    expect(reportResponse.status).toBe('generated')
    expect(reportResponse.report_url).toBeDefined()

    // 4. Verify all agents logged the interactions
    const auditLogs = await getAuditLogs()
    expect(auditLogs).toHaveLength(3) // 3 inter-agent calls
  })

  it('should handle agent failures gracefully', async () => {
    // Simulate analysis agent failure
    await stopAgent('analysis-agent')

    const response = await agents.coordinator.callAgent(
      'http://localhost:3003/analyze',
      { dataset_id: 'test-dataset' }
    )

    // Should handle timeout/connection error
    expect(response).toBeNull()
    
    // Coordinator should try fallback agent
    const fallbackResponse = await agents.coordinator.callAgent(
      'http://localhost:3005/analyze', // fallback agent
      { dataset_id: 'test-dataset' }
    )

    expect(fallbackResponse.status).toBe('analyzed')
  })
})
```

### Performance Testing

```typescript
// tests/performance/load-testing.test.ts
describe('Performance Testing', () => {
  describe('Authentication Load', () => {
    it('should handle 1000 concurrent authentications', async () => {
      const startTime = Date.now()
      
      const promises = Array.from({ length: 1000 }, async (_, i) => {
        const token = generateToken(
          { sub: `load-test-agent-${i}` },
          TEST_PRIVATE_KEY
        )
        
        return fetch('http://localhost:3000/protected', {
          headers: {
            'Authorization': `Bearer ${token}`,
            'x-phlow-agent-id': `load-test-agent-${i}`
          }
        })
      })

      const responses = await Promise.all(promises)
      const endTime = Date.now()

      const successCount = responses.filter(r => r.ok).length
      const duration = endTime - startTime

      expect(successCount).toBeGreaterThan(950) // 95% success rate
      expect(duration).toBeLessThan(10000) // Under 10 seconds
      
      console.log(`Processed ${successCount}/1000 requests in ${duration}ms`)
      console.log(`Average: ${duration / 1000}ms per request`)
    })
  })

  describe('Database Performance', () => {
    it('should perform agent lookups efficiently', async () => {
      // Create test agents
      const agentCount = 10000
      const agents = Array.from({ length: agentCount }, (_, i) => ({
        agentId: `perf-test-agent-${i}`,
        name: `Performance Test Agent ${i}`,
        publicKey: TEST_PUBLIC_KEY,
        skills: [{ name: `skill-${i % 10}` }]
      }))

      // Batch insert
      console.time('Bulk Insert')
      await bulkInsertAgents(agents)
      console.timeEnd('Bulk Insert')

      // Test individual lookups
      console.time('Individual Lookups')
      const lookupPromises = Array.from({ length: 100 }, () => {
        const randomId = `perf-test-agent-${Math.floor(Math.random() * agentCount)}`
        return helpers.getAgentCard(randomId)
      })
      
      await Promise.all(lookupPromises)
      console.timeEnd('Individual Lookups')

      // Test skill search
      console.time('Skill Search')
      const searchResults = await helpers.searchAgents({
        skills: ['skill-5']
      })
      console.timeEnd('Skill Search')

      expect(searchResults.length).toBeGreaterThan(0)
    })
  })

  describe('Rate Limiting Performance', () => {
    it('should enforce rate limits efficiently', async () => {
      const rateLimiter = new RateLimiter(100, 60) // 100 req/minute
      
      console.time('Rate Limit Checks')
      
      // Should allow first 100 requests
      for (let i = 0; i < 100; i++) {
        await rateLimiter.checkRateLimit('test-agent')
      }
      
      // Should reject 101st request
      let rejected = false
      try {
        await rateLimiter.checkRateLimit('test-agent')
      } catch (error) {
        rejected = true
      }
      
      console.timeEnd('Rate Limit Checks')
      
      expect(rejected).toBe(true)
    })
  })
})
```

## Test Utilities and Fixtures

### Test Data Generation

```typescript
// tests/utils/test-data.ts
export const TEST_KEY_PAIR = {
  private: `-----BEGIN RSA PRIVATE KEY-----
MIIEpAIBAAKCAQEA7Q1C...
-----END RSA PRIVATE KEY-----`,
  public: `-----BEGIN PUBLIC KEY-----
MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEA7Q1C...
-----END PUBLIC KEY-----`
}

export function createTestAgentCard(id: string): AgentCard {
  return {
    agentId: id,
    name: `Test Agent ${id}`,
    description: `Test agent for automated testing`,
    publicKey: TEST_KEY_PAIR.public,
    serviceUrl: `https://${id}.test.example.com`,
    permissions: ['read:data', 'write:test'],
    skills: [
      { name: 'testing', description: 'Automated testing capabilities' }
    ],
    metadata: {
      version: '1.0.0',
      environment: 'test',
      created_by: 'test-suite'
    }
  }
}

export async function createTestToken(
  subject: string,
  audience?: string,
  permissions?: string[]
): Promise<string> {
  return generateToken(
    {
      sub: subject,
      iss: subject,
      aud: audience || 'test-target',
      permissions: permissions || ['read:data']
    },
    TEST_KEY_PAIR.private,
    '1h'
  )
}
```

### Mock Servers

```python
# tests/fixtures/mock_agents.py
from fastapi import FastAPI, Depends
from phlow import PhlowMiddleware, PhlowConfig
from phlow.integrations.fastapi import FastAPIIntegration

def create_mock_agent_server(agent_id: str, port: int):
    """Create a mock agent server for testing."""
    app = FastAPI(title=f"Mock Agent: {agent_id}")
    
    config = PhlowConfig(
        supabase_url=os.getenv("TEST_SUPABASE_URL"),
        supabase_anon_key=os.getenv("TEST_SUPABASE_ANON_KEY"),
        agent_card=AgentCard(
            agent_id=agent_id,
            name=f"Mock Agent {agent_id}",
            public_key=TEST_PUBLIC_KEY
        ),
        private_key=TEST_PRIVATE_KEY
    )
    
    phlow = PhlowMiddleware(config)
    integration = FastAPIIntegration(phlow)
    auth_required = integration.create_auth_dependency()
    
    @app.get("/.well-known/agent.json")
    async def agent_card():
        return phlow.well_known_handler()
    
    @app.post("/process")
    async def process_data(
        request: dict,
        context: PhlowContext = Depends(auth_required)
    ):
        return {
            "status": "processed",
            "agent": agent_id,
            "data": request,
            "processed_by": context.agent.name
        }
    
    return app

if __name__ == "__main__":
    import uvicorn
    import sys
    
    agent_id = sys.argv[1] if len(sys.argv) > 1 else "mock-agent"
    port = int(sys.argv[2]) if len(sys.argv) > 2 else 8000
    
    app = create_mock_agent_server(agent_id, port)
    uvicorn.run(app, host="0.0.0.0", port=port)
```

## CI/CD Integration

### GitHub Actions Workflow

```yaml
# .github/workflows/test.yml
name: Test Suite

on: [push, pull_request]

jobs:
  unit-tests:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        node-version: [18, 20]
        python-version: ['3.8', '3.9', '3.10', '3.11']
    
    steps:
      - uses: actions/checkout@v3
      
      - name: Setup Node.js
        uses: actions/setup-node@v3
        with:
          node-version: ${{ matrix.node-version }}
          
      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: ${{ matrix.python-version }}
      
      - name: Install dependencies
        run: |
          npm install
          pip install -r packages/phlow-auth-python/requirements.txt
      
      - name: Run JavaScript tests
        run: |
          cd packages/phlow-auth-js
          npm test -- --coverage
      
      - name: Run Python tests
        run: |
          cd packages/phlow-auth-python
          pytest --cov=src/phlow --cov-report=xml
      
      - name: Upload coverage
        uses: codecov/codecov-action@v3
        with:
          files: ./packages/*/coverage.xml

  integration-tests:
    runs-on: ubuntu-latest
    needs: unit-tests
    
    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_PASSWORD: postgres
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
    
    steps:
      - uses: actions/checkout@v3
      
      - name: Setup Supabase
        run: |
          npx supabase start
          npx supabase db reset
      
      - name: Run integration tests
        env:
          TEST_SUPABASE_URL: http://localhost:54321
          TEST_SUPABASE_ANON_KEY: ${{ secrets.TEST_SUPABASE_ANON_KEY }}
        run: |
          npm run test:integration

  e2e-tests:
    runs-on: ubuntu-latest
    needs: integration-tests
    
    steps:
      - uses: actions/checkout@v3
      
      - name: Start test agents
        run: |
          docker-compose -f tests/docker-compose.test.yml up -d
          
      - name: Wait for agents
        run: |
          timeout 60 bash -c 'until curl -f http://localhost:3001/health; do sleep 2; done'
          timeout 60 bash -c 'until curl -f http://localhost:3002/health; do sleep 2; done'
      
      - name: Run E2E tests
        run: npm run test:e2e
      
      - name: Cleanup
        run: docker-compose -f tests/docker-compose.test.yml down
```

## Testing Best Practices

### Security Testing

1. **JWT Security**:
   - Test with expired tokens
   - Test with wrong signatures
   - Test with malformed tokens
   - Test algorithm confusion attacks

2. **Permission Testing**:
   - Verify permission inheritance
   - Test edge cases in permission checking
   - Validate RLS policy enforcement

3. **Input Validation**:
   - Test with malicious payloads
   - Validate all user inputs
   - Test boundary conditions

### Performance Testing

1. **Load Testing**:
   - Concurrent authentication requests
   - Database query performance
   - Memory usage under load

2. **Stress Testing**:
   - Rate limiting behavior
   - Graceful degradation
   - Resource exhaustion scenarios

### Test Organization

1. **Test Isolation**:
   - Each test should be independent
   - Clean test data between runs
   - Use test-specific agent IDs

2. **Test Data Management**:
   - Generate test data programmatically
   - Use factories for complex objects
   - Maintain test data consistency

3. **Assertion Quality**:
   - Test specific behaviors, not implementation
   - Use descriptive test names
   - Provide clear failure messages

---

This comprehensive testing strategy ensures the reliability, security, and performance of the Phlow authentication system across all components and use cases. The next section covers [Troubleshooting](troubleshooting.md) for common issues and debugging techniques.