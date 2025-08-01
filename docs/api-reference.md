# API Reference

This page documents the complete API for all Phlow packages. Use the tabs below to navigate between different language implementations.

=== "JavaScript/TypeScript"

    ### PhlowMiddleware

    The main middleware class for Phlow authentication.

    ```typescript
    class PhlowMiddleware {
      constructor(config: PhlowConfig)
      authenticate(options?: VerifyOptions): MiddlewareFunction
      refreshTokenIfNeeded(): MiddlewareFunction
      getSupabaseClient(): SupabaseClient
      getAgentCard(): AgentCard
    }
    ```

    #### Constructor

    ```typescript
    new PhlowMiddleware(config: PhlowConfig)
    ```

    **Parameters:**
    - `config`: Configuration object containing Supabase credentials, agent card, and options

    **Example:**
    ```typescript
    const phlow = new PhlowMiddleware({
      supabaseUrl: 'https://your-project.supabase.co',
      supabaseAnonKey: 'your-anon-key',
      agentCard: {
        agentId: 'my-agent',
        name: 'My Agent',
        permissions: ['read:data'],
        publicKey: 'RSA public key',
      },
      privateKey: 'RSA private key',
      options: {
        enableAudit: true,
        rateLimiting: {
          maxRequests: 100,
          windowMs: 60000,
        },
      },
    });
    ```

    #### authenticate()

    Creates Express middleware for authentication.

    ```typescript
    authenticate(options?: VerifyOptions): MiddlewareFunction
    ```

    **Parameters:**
    - `options.requiredPermissions?`: Array of required permissions
    - `options.allowExpired?`: Whether to allow expired tokens

    **Example:**
    ```typescript
    // Basic authentication
    app.get('/protected', phlow.authenticate(), handler);

    // Require specific permissions
    app.get('/admin', phlow.authenticate({
      requiredPermissions: ['admin:users']
    }), handler);

    // Allow expired tokens
    app.get('/refresh', phlow.authenticate({
      allowExpired: true
    }), handler);
    ```

    #### refreshTokenIfNeeded()

    Middleware to check if tokens need refreshing.

    ```typescript
    refreshTokenIfNeeded(): MiddlewareFunction
    ```

    **Example:**
    ```typescript
    app.use(phlow.refreshTokenIfNeeded());
    ```

    ### JWT Utilities

    #### generateToken()

    Generate a JWT token for agent authentication.

    ```typescript
    function generateToken(
      agentCard: AgentCard,
      privateKey: string,
      audience: string,
      expiresIn?: string
    ): string
    ```

    **Parameters:**
    - `agentCard`: The agent card containing agent information
    - `privateKey`: Private key to sign the token
    - `audience`: Target agent ID
    - `expiresIn`: Token expiration (default: '1h')

    **Example:**
    ```typescript
    import { generateToken } from 'phlow-auth';

    const token = generateToken(
      myAgentCard,
      myPrivateKey,
      'target-agent-id',
      '2h'
    );
    ```

    #### verifyToken()

    Verify a JWT token.

    ```typescript
    function verifyToken(
      token: string,
      publicKey: string,
      options?: {
        audience?: string;
        issuer?: string;
        ignoreExpiration?: boolean;
      }
    ): JWTClaims
    ```

    **Parameters:**
    - `token`: JWT token to verify
    - `publicKey`: Public key to verify signature
    - `options`: Verification options

    **Example:**
    ```typescript
    import { verifyToken } from 'phlow-auth';

    const claims = verifyToken(
      token,
      senderPublicKey,
      {
        audience: 'my-agent-id',
        issuer: 'sender-agent-id',
      }
    );
    ```

    #### decodeToken()

    Decode a JWT token without verification.

    ```typescript
    function decodeToken(token: string): JWTClaims | null
    ```

    #### isTokenExpired()

    Check if a token is expired.

    ```typescript
    function isTokenExpired(token: string, thresholdSeconds?: number): boolean
    ```

    ### SupabaseHelpers

    Helper class for Supabase operations.

    ```typescript
    class SupabaseHelpers {
      constructor(supabase: SupabaseClient)
      
      async registerAgentCard(agentCard: AgentCard): Promise<void>
      async getAgentCard(agentId: string): Promise<AgentCard | null>
      async listAgentCards(filters?: {
        permissions?: string[];
        metadata?: Record<string, any>;
      }): Promise<AgentCard[]>
      
      static generateRLSPolicy(tableName: string, policyName: string): string
      static generateAgentSpecificRLSPolicy(
        tableName: string, 
        policyName: string, 
        agentIdColumn?: string
      ): string
      static generatePermissionBasedRLSPolicy(
        tableName: string, 
        policyName: string, 
        requiredPermission: string
      ): string
    }
    ```

    **Example:**
    ```typescript
    import { SupabaseHelpers } from 'phlow-auth';

    const helpers = new SupabaseHelpers(supabaseClient);

    // Register agent
    await helpers.registerAgentCard(agentCard);

    // Get agent
    const agent = await helpers.getAgentCard('agent-id');

    // List agents with permissions
    const agents = await helpers.listAgentCards({
      permissions: ['read:data'],
      metadata: { environment: 'production' },
    });
    ```

    ### Types

    #### AgentCard

    ```typescript
    interface AgentCard {
      agentId: string;
      name: string;
      description?: string;
      permissions: string[];
      publicKey: string;
      endpoints?: {
        auth?: string;
        api?: string;
      };
      metadata?: Record<string, any>;
    }
    ```

    #### PhlowConfig

    ```typescript
    interface PhlowConfig {
      supabaseUrl: string;
      supabaseAnonKey: string;
      agentCard: AgentCard;
      privateKey: string;
      options?: {
        tokenExpiry?: string;
        refreshThreshold?: number;
        enableAudit?: boolean;
        rateLimiting?: {
          maxRequests: number;
          windowMs: number;
        };
      };
    }
    ```

    #### JWTClaims

    ```typescript
    interface JWTClaims {
      sub: string;      // Subject (agent ID)
      iss: string;      // Issuer (agent ID)
      aud: string;      // Audience (target agent ID)
      exp: number;      // Expiration time
      iat: number;      // Issued at time
      permissions: string[];
      metadata?: Record<string, any>;
    }
    ```

    #### PhlowContext

    ```typescript
    interface PhlowContext {
      agent: AgentCard;
      token: string;
      claims: JWTClaims;
      supabase: SupabaseClient;
    }
    ```

    ### Exceptions

    ```typescript
    class PhlowError extends Error {
      constructor(message: string, code: string, statusCode?: number)
    }

    class AuthenticationError extends PhlowError {}
    class AuthorizationError extends PhlowError {}
    class ConfigurationError extends PhlowError {}
    class TokenError extends PhlowError {}
    class RateLimitError extends PhlowError {}
    ```

=== "Python"

    ### PhlowMiddleware

    ```python
    class PhlowMiddleware:
        def __init__(self, config: PhlowConfig)
        
        async def authenticate(
            self,
            token: str,
            agent_id: str,
            options: Optional[VerifyOptions] = None
        ) -> PhlowContext
        
        def authenticate_sync(
            self,
            token: str,
            agent_id: str,
            options: Optional[VerifyOptions] = None
        ) -> PhlowContext
        
        async def check_token_refresh(self, token: str) -> bool
        def get_supabase_client(self) -> Client
        def get_agent_card(self) -> AgentCard
    ```

    **Example:**
    ```python
    from phlow import PhlowMiddleware, PhlowConfig, AgentCard

    config = PhlowConfig(
        supabase_url="https://your-project.supabase.co",
        supabase_anon_key="your-anon-key",
        agent_card=AgentCard(
            agent_id="my-agent",
            name="My Agent",
            permissions=["read:data"],
            public_key="RSA public key",
        ),
        private_key="RSA private key",
        enable_audit=True,
    )

    phlow = PhlowMiddleware(config)

    # Authenticate request
    context = await phlow.authenticate(token, agent_id)
    ```

    ### JWT Utilities

    ```python
    def generate_token(
        agent_card: AgentCard,
        private_key: str,
        audience: str,
        expires_in: str = "1h"
    ) -> str

    def verify_token(
        token: str,
        public_key: str,
        audience: Optional[str] = None,
        issuer: Optional[str] = None,
        ignore_expiration: bool = False
    ) -> JWTClaims

    def decode_token(token: str) -> Optional[JWTClaims]

    def is_token_expired(token: str, threshold_seconds: int = 0) -> bool
    ```

    ### SupabaseHelpers

    ```python
    class SupabaseHelpers:
        def __init__(self, supabase_client: Client)
        
        async def register_agent_card(self, agent_card: AgentCard) -> None
        def register_agent_card_sync(self, agent_card: AgentCard) -> None
        
        async def get_agent_card(self, agent_id: str) -> Optional[AgentCard]
        def get_agent_card_sync(self, agent_id: str) -> Optional[AgentCard]
        
        async def list_agent_cards(
            self,
            permissions: Optional[List[str]] = None,
            metadata_filters: Optional[Dict[str, Any]] = None
        ) -> List[AgentCard]
        
        @staticmethod
        def generate_rls_policy(table_name: str, policy_name: str) -> str
        
        @staticmethod
        def generate_agent_specific_rls_policy(
            table_name: str,
            policy_name: str,
            agent_id_column: str = "agent_id"
        ) -> str
        
        @staticmethod
        def generate_permission_based_rls_policy(
            table_name: str,
            policy_name: str,
            required_permission: str
        ) -> str
    ```

    ### FastAPI Integration

    ```python
    from phlow.integrations.fastapi import create_phlow_dependency
    from fastapi import FastAPI, Depends

    app = FastAPI()

    # Create auth dependency
    auth_required = create_phlow_dependency(phlow)
    admin_required = create_phlow_dependency(
        phlow, 
        required_permissions=["admin:users"]
    )

    @app.get("/protected")
    async def protected_endpoint(context = Depends(auth_required)):
        return {"agent": context.agent.name}

    @app.get("/admin")
    async def admin_endpoint(context = Depends(admin_required)):
        return {"message": "Admin access granted"}
    ```

    ### Types

    #### AgentCard

    ```python
    class AgentCard(BaseModel):
        agent_id: str
        name: str
        description: Optional[str] = None
        permissions: List[str] = []
        public_key: str
        endpoints: Optional[Dict[str, str]] = None
        metadata: Optional[Dict[str, Any]] = None
    ```

    #### PhlowConfig

    ```python
    class PhlowConfig(BaseModel):
        supabase_url: str
        supabase_anon_key: str
        agent_card: AgentCard
        private_key: str
        token_expiry: str = "1h"
        refresh_threshold: int = 300
        enable_audit: bool = False
        rate_limiting: Optional[Dict[str, int]] = None
    ```

    #### JWTClaims

    ```python
    class JWTClaims(BaseModel):
        sub: str
        iss: str
        aud: str
        exp: int
        iat: int
        permissions: List[str] = []
        metadata: Optional[Dict[str, Any]] = None
    ```

    ### Exceptions

    ```python
    class PhlowError(Exception):
        def __init__(self, message: str, code: str = "PHLOW_ERROR", status_code: int = 500)

    class AuthenticationError(PhlowError): pass
    class AuthorizationError(PhlowError): pass
    class ConfigurationError(PhlowError): pass
    class TokenError(PhlowError): pass
    class RateLimitError(PhlowError): pass
    ```

=== "CLI Tools"

    ### phlow init

    Initialize a new Phlow project.

    ```bash
    phlow init [options]
    ```

    **Options:**
    - `-f, --force` - Overwrite existing configuration

    **Interactive prompts:**
    - Supabase URL
    - Supabase anon key
    - Agent ID
    - Agent name
    - Agent description
    - Permissions
    - Generate new RSA key pair

    ### phlow generate-card

    Generate and register agent card.

    ```bash
    phlow generate-card [options]
    ```

    **Options:**
    - `-o, --output <file>` - Output file for agent card JSON
    - `--no-register` - Don't register with Supabase

    ### phlow dev-start

    Start local development environment.

    ```bash
    phlow dev-start [options]
    ```

    **Options:**
    - `-p, --port <port>` - Port for development server (default: 3000)
    - `-d, --dir <directory>` - Directory to create dev project (default: ./phlow-dev-agent)

    ### phlow test-token

    Generate test tokens for authentication.

    ```bash
    phlow test-token [options] [token]
    ```

    **Options:**
    - `-t, --target <agentId>` - Target agent ID (default: test-agent)
    - `-e, --expires <duration>` - Token expiration (default: 1h)
    - `--decode` - Decode and display an existing token

    **Arguments:**
    - `token` - Token to decode (when using --decode)

=== "Development Tools"

    ### DevServer

    Development server with mock Supabase and test scenarios.

    ```typescript
    import { DevServer } from 'phlow-dev';

    const server = new DevServer({
      port: 3000,
      enableCors: true,
      enableTestEndpoints: true,
      mockAgents: [agentCard1, agentCard2],
    });

    // Initialize mock Supabase
    server.initializeMockSupabase();

    // Add Phlow middleware
    server.addPhlowMiddleware(middleware, '/protected');

    // Add custom routes
    server.addCustomRoute('get', '/custom', handler);

    // Start server
    await server.start();
    ```

    ### TestRunner

    Run predefined test scenarios.

    ```typescript
    import { TestRunner, TEST_SCENARIOS } from 'phlow-dev';

    const runner = new TestRunner();

    // Run all scenarios
    const results = await runner.runAllScenarios();

    // Run specific scenario
    const scenario = TEST_SCENARIOS.find(s => s.name === 'valid_jwt_authentication');
    const result = await runner.runScenario(scenario);
    ```

    ### MockSupabase

    Mock Supabase client for testing.

    ```typescript
    import { createMockSupabase } from 'phlow-dev';

    const mockSupabase = createMockSupabase({
      agents: [agentCard1, agentCard2],
      enableAuditLogs: true,
    });

    // Use like regular Supabase client
    const result = await mockSupabase.from('agent_cards').select('*');
    ```

=== "Reference"

    ## HTTP Headers

    ### Request Headers

    **Required:**
    - `Authorization: Bearer <jwt-token>` - JWT token for authentication
    - `X-Phlow-Agent-Id: <agent-id>` - Agent ID of the requesting agent

    **Optional:**
    - `Content-Type: application/json` - For POST/PUT requests

    ### Response Headers

    **Authentication:**
    - `X-Phlow-Token-Refresh: true` - Indicates token should be refreshed

    **Errors:**
    - `WWW-Authenticate: Bearer` - For 401 responses

    ## Error Codes

    ### Authentication Errors (401)

    - `TOKEN_MISSING` - No token provided
    - `TOKEN_INVALID` - Invalid token format or signature
    - `TOKEN_EXPIRED` - Token has expired
    - `AGENT_NOT_FOUND` - Agent not found in database
    - `AGENT_ID_MISSING` - Agent ID header not provided

    ### Authorization Errors (403)

    - `INSUFFICIENT_PERMISSIONS` - Agent lacks required permissions

    ### Rate Limiting (429)

    - `RATE_LIMIT` - Rate limit exceeded

    ### Configuration Errors (500)

    - `CONFIG_ERROR` - Invalid configuration
    - `SUPABASE_ERROR` - Supabase connection or query error

    ## Database Schema

    ### agent_cards

    | Column | Type | Description |
    |--------|------|-------------|
    | id | UUID | Primary key |
    | agent_id | TEXT | Unique agent identifier |
    | name | TEXT | Human-readable name |
    | description | TEXT | Optional description |
    | permissions | TEXT[] | Array of permissions |
    | public_key | TEXT | RSA public key (PEM format) |
    | endpoints | JSONB | API endpoints |
    | metadata | JSONB | Custom metadata |
    | created_at | TIMESTAMPTZ | Creation timestamp |
    | updated_at | TIMESTAMPTZ | Last update timestamp |

    ### phlow_audit_logs

    | Column | Type | Description |
    |--------|------|-------------|
    | id | UUID | Primary key |
    | timestamp | TIMESTAMPTZ | Event timestamp |
    | event | TEXT | Event type |
    | agent_id | TEXT | Agent that triggered event |
    | target_agent_id | TEXT | Target agent (optional) |
    | details | JSONB | Additional event details |
    | created_at | TIMESTAMPTZ | Record creation timestamp |

    ## RLS Policies

    ### Basic Agent Access

    ```sql
    CREATE POLICY agent_access ON table_name
    FOR ALL
    USING (
      auth.jwt() ->> 'sub' IS NOT NULL
      AND EXISTS (
        SELECT 1 FROM agent_cards
        WHERE agent_id = auth.jwt() ->> 'sub'
      )
    );
    ```

    ### Agent-Specific Access

    ```sql
    CREATE POLICY agent_own_data ON table_name
    FOR ALL
    USING (agent_id = auth.jwt() ->> 'sub');
    ```

    ### Permission-Based Access

    ```sql
    CREATE POLICY admin_only ON table_name
    FOR ALL
    USING (auth.jwt() -> 'permissions' ? 'admin:users');
    ```