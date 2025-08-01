# Python Implementation

This guide provides an in-depth look at the Python implementation of Phlow authentication, covering the async-first architecture, framework integrations, and advanced features.

## Package Overview

**Location**: `/packages/phlow-auth-python/`
**Package Name**: `phlow-auth` (PyPI)
**Language**: Python 3.8+ with type annotations
**Build Tool**: Hatchling (modern Python packaging)
**Key Features**: Async/sync dual APIs, Pydantic validation, framework integrations

## Architecture

### Core Design Principles

**1. Async-First with Sync Wrappers**:
```python
# Primary async API
async def authenticate(self, token: str, agent_id: str) -> PhlowContext

# Sync wrapper for compatibility
def authenticate_sync(self, token: str, agent_id: str) -> PhlowContext:
    return asyncio.run(self.authenticate(token, agent_id))
```

**2. Pydantic Data Validation**:
```python
class AgentCard(BaseModel):
    agent_id: str
    name: str
    permissions: List[str] = []
    # Automatic validation and serialization
```

**3. Framework Integration Pattern**:
```python
# Dependency injection for FastAPI
def create_auth_dependency(self) -> Callable:
    async def auth_dependency(request: Request) -> PhlowContext:
        # Extract and validate authentication
```

## Core Components

### PhlowMiddleware Class

**File**: `src/phlow/middleware.py`

```python
from typing import Optional, List, Dict, Any
from dataclasses import dataclass
import asyncio
import logging

class PhlowMiddleware:
    def __init__(self, config: PhlowConfig):
        self.config = self._validate_config(config)
        self.supabase = create_client(config.supabase_url, config.supabase_anon_key)
        self.supabase_helpers = SupabaseHelpers(self.supabase)
        self.rate_limiter = RateLimiter() if config.rate_limiting else None
        self.audit_logger = AuditLogger(config.audit_config) if config.audit_config else None
        
    async def authenticate(
        self, 
        token: str, 
        agent_id: str, 
        options: Optional[VerifyOptions] = None
    ) -> PhlowContext:
        """
        Core async authentication method.
        
        Args:
            token: JWT token from Authorization header
            agent_id: Agent ID from x-phlow-agent-id header
            options: Optional verification settings
            
        Returns:
            PhlowContext with authenticated agent info
            
        Raises:
            AuthenticationError: If authentication fails
            AuthorizationError: If permissions insufficient
            RateLimitError: If rate limit exceeded
        """
        try:
            # Rate limiting check
            if self.rate_limiter:
                await self.rate_limiter.check_rate_limit(agent_id)
            
            # Get agent card from database
            agent_card = await self.supabase_helpers.get_agent_card(agent_id)
            if not agent_card:
                raise AuthenticationError(f"Agent not found: {agent_id}")
            
            # Verify JWT token
            claims = await verify_token(token, agent_card.public_key)
            
            # Validate claims
            self._validate_claims(claims, agent_card, options)
            
            # Check permissions if specified
            if options and options.required_permissions:
                self._check_permissions(claims, options.required_permissions)
            
            # Audit logging
            if self.audit_logger:
                await self.audit_logger.log_auth_attempt(
                    AuthEvent(
                        agent_id=agent_id,
                        success=True,
                        permissions=claims.get('permissions', []),
                        timestamp=datetime.utcnow()
                    )
                )
            
            return PhlowContext(
                agent=agent_card,
                token=token,
                claims=claims,
                supabase=self.supabase
            )
            
        except Exception as e:
            # Audit failed attempts
            if self.audit_logger:
                await self.audit_logger.log_auth_attempt(
                    AuthEvent(
                        agent_id=agent_id,
                        success=False,
                        error=str(e),
                        timestamp=datetime.utcnow()
                    )
                )
            raise

    def authenticate_sync(self, token: str, agent_id: str) -> PhlowContext:
        """Synchronous wrapper for authenticate method."""
        return asyncio.run(self.authenticate(token, agent_id))

    def well_known_handler(self) -> Dict[str, Any]:
        """
        A2A Protocol discovery endpoint handler.
        
        Returns:
            Agent card in A2A-compatible format
        """
        agent_card = self.config.agent_card
        return {
            "schemaVersion": "1.0",
            "agentId": agent_card.agent_id,
            "name": agent_card.name,
            "description": agent_card.description,
            "serviceUrl": agent_card.service_url,
            "publicKey": agent_card.public_key,
            "skills": [
                {"name": skill.name, "description": skill.description}
                for skill in agent_card.skills
            ] if agent_card.skills else [],
            "securitySchemes": {
                "bearer": {
                    "type": "bearer",
                    "scheme": "bearer"
                }
            },
            "endpoints": agent_card.endpoints or {},
            "metadata": agent_card.metadata or {}
        }

    async def call_agent(
        self, 
        url: str, 
        data: Dict[str, Any], 
        options: Optional[CallOptions] = None
    ) -> Any:
        """
        Make authenticated request to another agent.
        
        Args:
            url: Target agent endpoint URL
            data: Request payload
            options: Optional request settings
            
        Returns:
            Response data from target agent
        """
        import httpx
        
        # Generate JWT token for the request
        token = await generate_token(
            claims={
                "sub": self.config.agent_card.agent_id,
                "iss": self.config.agent_card.agent_id,
                "aud": self._extract_agent_id_from_url(url),
                "permissions": self.config.agent_card.permissions or []
            },
            private_key=self.config.private_key,
            expires_in=options.expires_in if options else "1h"
        )
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}",
            "x-phlow-agent-id": self.config.agent_card.agent_id
        }
        
        if options and options.headers:
            headers.update(options.headers)
        
        timeout = options.timeout if options else 30.0
        
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(url, json=data, headers=headers)
            response.raise_for_status()
            return response.json()

    def _validate_config(self, config: PhlowConfig) -> PhlowConfig:
        """Validate configuration on initialization."""
        if not config.supabase_url:
            raise ConfigurationError("supabase_url is required")
        if not config.supabase_anon_key:
            raise ConfigurationError("supabase_anon_key is required")
        if not config.private_key:
            raise ConfigurationError("private_key is required")
        
        # Validate private key format
        if not ("BEGIN RSA PRIVATE KEY" in config.private_key or 
                "BEGIN PRIVATE KEY" in config.private_key):
            raise ConfigurationError("Invalid private key format")
        
        return config

    def _validate_claims(
        self, 
        claims: Dict[str, Any], 
        agent_card: AgentCard, 
        options: Optional[VerifyOptions]
    ) -> None:
        """Validate JWT claims against agent card and options."""
        # Check token expiration (with optional tolerance)
        if not options or not options.allow_expired:
            exp = claims.get('exp')
            if exp and exp < time.time():
                raise TokenError("Token has expired")
        
        # Validate issuer matches agent ID
        if claims.get('iss') != agent_card.agent_id:
            raise AuthenticationError("Token issuer does not match agent ID")

    def _check_permissions(
        self, 
        claims: Dict[str, Any], 
        required_permissions: List[str]
    ) -> None:
        """Check if JWT claims contain required permissions."""
        token_permissions = set(claims.get('permissions', []))
        required_permissions_set = set(required_permissions)
        
        if not required_permissions_set.issubset(token_permissions):
            missing = required_permissions_set - token_permissions
            raise AuthorizationError(
                f"Missing required permissions: {', '.join(missing)}"
            )
```

### JWT Operations

**File**: `src/phlow/jwt_utils.py`

```python
import jwt
import time
import asyncio
from typing import Dict, Any, Union
from cryptography.hazmat.primitives import serialization
from datetime import datetime, timedelta

async def generate_token(
    claims: Dict[str, Any],
    private_key: str,
    expires_in: str = "1h"
) -> str:
    """
    Generate a signed JWT token.
    
    Args:
        claims: JWT payload claims
        private_key: RSA private key in PEM format
        expires_in: Token expiration (e.g., "1h", "30m", "3600s")
        
    Returns:
        Signed JWT token string
    """
    # Parse expiration time
    expiry_seconds = _parse_expiry(expires_in)
    
    # Add standard claims
    now = int(time.time())
    full_claims = {
        **claims,
        "iat": now,
        "exp": now + expiry_seconds
    }
    
    # Load private key
    try:
        private_key_obj = serialization.load_pem_private_key(
            private_key.encode("utf-8"),
            password=None
        )
    except Exception as e:
        raise TokenError(f"Failed to load private key: {e}")
    
    # Sign token
    try:
        token = jwt.encode(full_claims, private_key_obj, algorithm="RS256")
        return token
    except Exception as e:
        raise TokenError(f"Failed to generate token: {e}")

async def verify_token(token: str, public_key: str) -> Dict[str, Any]:
    """
    Verify JWT token signature and decode claims.
    
    Args:
        token: JWT token to verify
        public_key: RSA public key in PEM format
        
    Returns:
        Decoded JWT claims
        
    Raises:
        TokenError: If token is invalid, expired, or verification fails
    """
    try:
        # Load public key
        public_key_obj = serialization.load_pem_public_key(
            public_key.encode("utf-8")
        )
        
        # Verify and decode token
        decoded = jwt.decode(
            token,
            public_key_obj,
            algorithms=["RS256"]
        )
        
        return decoded
        
    except jwt.ExpiredSignatureError:
        raise TokenError("Token has expired", "TOKEN_EXPIRED")
    except jwt.InvalidTokenError as e:
        raise TokenError(f"Invalid token: {e}", "TOKEN_INVALID")
    except Exception as e:
        raise TokenError(f"Token verification failed: {e}", "TOKEN_VERIFICATION_FAILED")

def decode_token_unsafe(token: str) -> Dict[str, Any]:
    """
    Decode JWT token without signature verification.
    
    WARNING: This does not verify the token signature!
    Only use for inspection purposes.
    
    Args:
        token: JWT token to decode
        
    Returns:
        Decoded JWT claims (unverified)
    """
    return jwt.decode(token, options={"verify_signature": False})

def is_token_expired(token: str, threshold_seconds: int = 300) -> bool:
    """
    Check if token is expired or will expire soon.
    
    Args:
        token: JWT token to check
        threshold_seconds: Consider expired if expires within this time
        
    Returns:
        True if token is expired or expiring soon
    """
    try:
        claims = decode_token_unsafe(token)
        exp = claims.get('exp')
        if not exp:
            return True
        
        return exp < (time.time() + threshold_seconds)
    except Exception:
        return True

def _parse_expiry(expires_in: str) -> int:
    """
    Parse expiry string to seconds.
    
    Supports: 30s, 15m, 2h, 1d
    """
    import re
    
    match = re.match(r'^(\d+)([smhd])$', expires_in.lower())
    if not match:
        raise ValueError(f"Invalid expiry format: {expires_in}")
    
    value = int(match.group(1))
    unit = match.group(2)
    
    multipliers = {
        's': 1,
        'm': 60,
        'h': 3600,
        'd': 86400
    }
    
    return value * multipliers[unit]
```

### Type System with Pydantic

**File**: `src/phlow/types.py`

```python
from pydantic import BaseModel, Field, validator
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime

class AgentCard(BaseModel):
    """Agent card model with Pydantic validation."""
    
    agent_id: str = Field(..., min_length=1, description="Unique agent identifier")
    name: str = Field(..., min_length=1, description="Human-readable agent name")
    description: Optional[str] = Field(None, description="Agent description")
    public_key: str = Field(..., description="RSA public key in PEM format")
    service_url: Optional[str] = Field(None, description="Base URL for agent services")
    permissions: List[str] = Field(default_factory=list, description="Agent permissions")
    skills: List[Dict[str, str]] = Field(default_factory=list, description="Agent capabilities")
    security_schemes: Optional[Dict[str, Any]] = Field(None, description="Supported auth schemes")
    endpoints: Optional[Dict[str, Any]] = Field(None, description="Available endpoints")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")
    
    @validator('public_key')
    def validate_public_key(cls, v):
        if not ("BEGIN PUBLIC KEY" in v or "BEGIN RSA PUBLIC KEY" in v):
            raise ValueError("Invalid public key format")
        return v
    
    @validator('permissions')
    def validate_permissions(cls, v):
        # Validate permission format: action:resource
        for perm in v:
            if ':' not in perm:
                raise ValueError(f"Invalid permission format: {perm}")
        return v
    
    class Config:
        schema_extra = {
            "example": {
                "agent_id": "data-analyzer",
                "name": "Data Analysis Agent",
                "description": "Specialized in statistical analysis",
                "public_key": "-----BEGIN PUBLIC KEY-----...",
                "permissions": ["read:data", "write:analysis"],
                "skills": [
                    {"name": "statistical-analysis", "description": "Statistical analysis"},
                    {"name": "data-visualization", "description": "Chart generation"}
                ]
            }
        }

class PhlowConfig(BaseModel):
    """Phlow middleware configuration."""
    
    supabase_url: str = Field(..., description="Supabase project URL")
    supabase_anon_key: str = Field(..., description="Supabase anonymous key")
    agent_card: AgentCard = Field(..., description="This agent's card")
    private_key: str = Field(..., description="RSA private key in PEM format")
    token_expiry: str = Field("1h", description="Default token expiry time")
    debug: bool = Field(False, description="Enable debug logging")
    rate_limiting: Optional['RateLimitConfig'] = Field(None, description="Rate limiting config")
    audit_config: Optional['AuditConfig'] = Field(None, description="Audit logging config")
    
    @validator('private_key')
    def validate_private_key(cls, v):
        if not ("BEGIN RSA PRIVATE KEY" in v or "BEGIN PRIVATE KEY" in v):
            raise ValueError("Invalid private key format")
        return v
    
    class Config:
        validate_assignment = True

class RateLimitConfig(BaseModel):
    """Rate limiting configuration."""
    
    max_requests: int = Field(100, description="Max requests per window")
    window_seconds: int = Field(3600, description="Time window in seconds")
    storage_backend: str = Field("memory", description="Storage backend (memory, redis)")
    redis_url: Optional[str] = Field(None, description="Redis URL for distributed limiting")

class AuditConfig(BaseModel):
    """Audit logging configuration."""
    
    enabled: bool = Field(True, description="Enable audit logging")
    log_level: str = Field("INFO", description="Log level")
    output_format: str = Field("json", description="Log format (json, text)")
    include_request_body: bool = Field(False, description="Include request bodies")

@dataclass
class PhlowContext:
    """Runtime context for authenticated requests."""
    
    agent: AgentCard
    token: str
    claims: Dict[str, Any]
    supabase: Any  # Supabase client

@dataclass
class VerifyOptions:
    """Token verification options."""
    
    required_permissions: Optional[List[str]] = None
    allow_expired: bool = False
    max_age_seconds: Optional[int] = None

@dataclass
class CallOptions:
    """Options for calling other agents."""
    
    expires_in: str = "1h"
    headers: Optional[Dict[str, str]] = None
    timeout: float = 30.0

@dataclass
class AuthEvent:
    """Audit log event for authentication attempts."""
    
    agent_id: str
    success: bool
    permissions: List[str]
    timestamp: datetime
    error: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
```

### FastAPI Integration

**File**: `src/phlow/integrations/fastapi.py`

```python
from fastapi import Request, Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Callable, List, Optional
import logging

logger = logging.getLogger(__name__)

class FastAPIIntegration:
    """FastAPI framework integration for Phlow authentication."""
    
    def __init__(self, middleware: 'PhlowMiddleware'):
        self.middleware = middleware
        self.security = HTTPBearer(auto_error=False)
    
    def create_auth_dependency(
        self,
        required_permissions: Optional[List[str]] = None,
        allow_expired: bool = False
    ) -> Callable:
        """
        Create FastAPI dependency for authentication.
        
        Args:
            required_permissions: List of required permissions
            allow_expired: Whether to allow expired tokens
            
        Returns:
            FastAPI dependency function
        """
        async def auth_dependency(
            request: Request,
            credentials: Optional[HTTPAuthorizationCredentials] = Depends(self.security)
        ) -> PhlowContext:
            try:
                # Extract token
                if not credentials:
                    raise HTTPException(
                        status_code=401,
                        detail="Missing Authorization header"
                    )
                
                token = credentials.credentials
                
                # Extract agent ID from headers
                agent_id = (
                    request.headers.get("x-phlow-agent-id") or
                    request.headers.get("X-Phlow-Agent-Id")
                )
                
                if not agent_id:
                    raise HTTPException(
                        status_code=400,
                        detail="Missing x-phlow-agent-id header"
                    )
                
                # Authenticate with middleware
                options = VerifyOptions(
                    required_permissions=required_permissions,
                    allow_expired=allow_expired
                )
                
                context = await self.middleware.authenticate(token, agent_id, options)
                
                # Store context in request state for later access
                request.state.phlow_context = context
                
                return context
                
            except PhlowError as e:
                logger.warning(f"Authentication failed: {e.message}")
                raise HTTPException(
                    status_code=e.status_code,
                    detail={
                        "error": e.message,
                        "code": e.code
                    }
                )
            except Exception as e:
                logger.error(f"Unexpected authentication error: {e}")
                raise HTTPException(
                    status_code=500,
                    detail="Internal authentication error"
                )
        
        return auth_dependency
    
    def require_auth(
        self,
        required_permissions: Optional[List[str]] = None,
        allow_expired: bool = False
    ) -> Callable:
        """
        Decorator for protecting FastAPI endpoints.
        
        Args:
            required_permissions: List of required permissions
            allow_expired: Whether to allow expired tokens
            
        Returns:
            Decorator function
        """
        def decorator(func: Callable) -> Callable:
            # Get the auth dependency
            auth_dep = self.create_auth_dependency(required_permissions, allow_expired)
            
            # Add dependency to function
            if not hasattr(func, '__dependencies__'):
                func.__dependencies__ = []
            func.__dependencies__.append(Depends(auth_dep))
            
            return func
        
        return decorator

# Usage example
def create_fastapi_app():
    """Example of creating FastAPI app with Phlow authentication."""
    from fastapi import FastAPI
    
    app = FastAPI(title="Phlow FastAPI Example")
    
    # Configure Phlow
    config = PhlowConfig(
        supabase_url=os.getenv("SUPABASE_URL"),
        supabase_anon_key=os.getenv("SUPABASE_ANON_KEY"),
        agent_card=AgentCard(
            agent_id="example-agent",
            name="Example Agent",
            public_key=os.getenv("PUBLIC_KEY")
        ),
        private_key=os.getenv("PRIVATE_KEY")
    )
    
    phlow = PhlowMiddleware(config)
    fastapi_integration = FastAPIIntegration(phlow)
    
    # Create auth dependencies
    auth_required = fastapi_integration.create_auth_dependency()
    admin_required = fastapi_integration.create_auth_dependency(
        required_permissions=["admin:write"]
    )
    
    # Agent card discovery endpoint
    @app.get("/.well-known/agent.json")
    async def agent_card():
        return phlow.well_known_handler()
    
    # Protected endpoint
    @app.get("/protected")
    async def protected_endpoint(context: PhlowContext = Depends(auth_required)):
        return {
            "message": "Access granted",
            "agent": context.agent.name,
            "permissions": context.claims.get("permissions", [])
        }
    
    # Admin-only endpoint
    @app.delete("/admin/data/{item_id}")
    async def delete_data(
        item_id: str,
        context: PhlowContext = Depends(admin_required)
    ):
        return {"message": f"Deleted item {item_id}", "deleted_by": context.agent.name}
    
    # Agent-to-agent communication
    @app.post("/analyze")
    async def analyze_data(
        request: dict,
        context: PhlowContext = Depends(auth_required)
    ):
        # Call another agent
        result = await phlow.call_agent(
            "https://data-processor.ai/process",
            {"data": request.get("data")}
        )
        return result
    
    return app
```

### Advanced Features

#### Rate Limiting

**File**: `src/phlow/rate_limiter.py`

```python
import time
import asyncio
from typing import Dict, Optional
from collections import defaultdict, deque

class RateLimiter:
    """In-memory rate limiter with sliding window."""
    
    def __init__(self, max_requests: int = 100, window_seconds: int = 3600):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests: Dict[str, deque] = defaultdict(deque)
        self._lock = asyncio.Lock()
    
    async def check_rate_limit(self, key: str) -> bool:
        """
        Check if request should be rate limited.
        
        Args:
            key: Rate limiting key (usually agent ID)
            
        Returns:
            True if request is allowed, False if rate limited
            
        Raises:
            RateLimitError: If rate limit exceeded
        """
        async with self._lock:
            now = time.time()
            cutoff = now - self.window_seconds
            
            # Clean old requests
            requests = self.requests[key]
            while requests and requests[0] < cutoff:
                requests.popleft()
            
            # Check limit
            if len(requests) >= self.max_requests:
                raise RateLimitError(
                    f"Rate limit exceeded: {len(requests)}/{self.max_requests} "
                    f"requests in {self.window_seconds} seconds"
                )
            
            # Record this request
            requests.append(now)
            return True
    
    def reset_limits(self, key: str) -> None:
        """Reset rate limits for a specific key."""
        if key in self.requests:
            del self.requests[key]
    
    def get_remaining(self, key: str) -> int:
        """Get remaining requests for a key."""
        requests = self.requests.get(key, deque())
        return max(0, self.max_requests - len(requests))
```

#### Audit Logging

**File**: `src/phlow/audit.py`

```python
import json
import logging
import asyncio
from typing import List, Optional
from datetime import datetime
from dataclasses import asdict

class AuditLogger:
    """Audit logger for authentication events."""
    
    def __init__(self, config: AuditConfig):
        self.config = config
        self.logger = logging.getLogger('phlow.audit')
        self.logger.setLevel(getattr(logging, config.log_level))
        
        # Configure formatter
        if config.output_format == 'json':
            formatter = logging.Formatter('%(message)s')
        else:
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
        
        handler = logging.StreamHandler()
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)
    
    async def log_auth_attempt(self, event: AuthEvent) -> None:
        """Log authentication attempt."""
        if not self.config.enabled:
            return
        
        event_data = asdict(event)
        event_data['timestamp'] = event.timestamp.isoformat()
        
        if self.config.output_format == 'json':
            message = json.dumps(event_data)
        else:
            status = "SUCCESS" if event.success else "FAILED"
            message = f"Auth {status} for agent {event.agent_id}"
        
        if event.success:
            self.logger.info(message)
        else:
            self.logger.warning(message)
    
    async def log_permission_check(self, event: PermissionEvent) -> None:
        """Log permission check."""
        if not self.config.enabled:
            return
        
        event_data = {
            'type': 'permission_check',
            'agent_id': event.agent_id,
            'required_permissions': event.required_permissions,
            'granted': event.granted,
            'timestamp': event.timestamp.isoformat()
        }
        
        if self.config.output_format == 'json':
            message = json.dumps(event_data)
        else:
            status = "GRANTED" if event.granted else "DENIED"
            message = f"Permission {status} for agent {event.agent_id}"
        
        self.logger.info(message)

@dataclass
class PermissionEvent:
    """Permission check audit event."""
    
    agent_id: str
    required_permissions: List[str]
    granted: bool
    timestamp: datetime
```

## Framework Integrations

### Flask Integration (Planned)

```python
# src/phlow/integrations/flask.py
from flask import request, g, jsonify
from functools import wraps

class FlaskIntegration:
    def __init__(self, middleware: PhlowMiddleware):
        self.middleware = middleware
    
    def require_auth(self, required_permissions: Optional[List[str]] = None):
        def decorator(f):
            @wraps(f)
            async def decorated_function(*args, **kwargs):
                # Extract token and agent ID from Flask request
                auth_header = request.headers.get('Authorization')
                if not auth_header or not auth_header.startswith('Bearer '):
                    return jsonify({'error': 'Missing authorization'}), 401
                
                token = auth_header[7:]
                agent_id = request.headers.get('x-phlow-agent-id')
                
                try:
                    context = await self.middleware.authenticate(token, agent_id)
                    g.phlow_context = context
                    return await f(*args, **kwargs)
                except PhlowError as e:
                    return jsonify({'error': e.message}), e.status_code
            
            return decorated_function
        return decorator
```

## Testing Patterns

### Unit Testing with pytest

```python
# tests/test_middleware.py
import pytest
from unittest.mock import AsyncMock, Mock
from phlow import PhlowMiddleware, PhlowConfig, AgentCard

@pytest.fixture
def config():
    return PhlowConfig(
        supabase_url="https://test.supabase.co",
        supabase_anon_key="test-key",
        agent_card=AgentCard(
            agent_id="test-agent",
            name="Test Agent",
            public_key=TEST_PUBLIC_KEY
        ),
        private_key=TEST_PRIVATE_KEY
    )

@pytest.fixture
def middleware(config):
    return PhlowMiddleware(config)

@pytest.mark.asyncio
async def test_authenticate_success(middleware):
    # Mock Supabase helper
    middleware.supabase_helpers.get_agent_card = AsyncMock(return_value=AgentCard(
        agent_id="requesting-agent",
        name="Requesting Agent",
        public_key=TEST_PUBLIC_KEY
    ))
    
    # Generate valid token
    token = await generate_token(
        {"sub": "requesting-agent", "iss": "requesting-agent"},
        TEST_PRIVATE_KEY
    )
    
    # Test authentication
    context = await middleware.authenticate(token, "requesting-agent")
    
    assert context.agent.agent_id == "requesting-agent"
    assert context.token == token

@pytest.mark.asyncio
async def test_authenticate_invalid_token(middleware):
    middleware.supabase_helpers.get_agent_card = AsyncMock(return_value=AgentCard(
        agent_id="test-agent",
        name="Test Agent", 
        public_key=TEST_PUBLIC_KEY
    ))
    
    with pytest.raises(TokenError):
        await middleware.authenticate("invalid-token", "test-agent")

@pytest.mark.asyncio
async def test_rate_limiting(middleware):
    # Configure rate limiter
    middleware.rate_limiter = RateLimiter(max_requests=1, window_seconds=60)
    
    # First request should succeed
    await middleware.rate_limiter.check_rate_limit("test-agent")
    
    # Second request should fail
    with pytest.raises(RateLimitError):
        await middleware.rate_limiter.check_rate_limit("test-agent")
```

### Integration Testing

```python
# tests/test_fastapi_integration.py
import pytest
from fastapi.testclient import TestClient
from phlow.integrations.fastapi import create_fastapi_app

@pytest.fixture
def app():
    return create_fastapi_app()

@pytest.fixture
def client(app):
    return TestClient(app)

def test_agent_card_endpoint(client):
    response = client.get("/.well-known/agent.json")
    assert response.status_code == 200
    data = response.json()
    assert "agentId" in data
    assert "publicKey" in data

def test_protected_endpoint_without_auth(client):
    response = client.get("/protected")
    assert response.status_code == 401

def test_protected_endpoint_with_auth(client):
    # Generate valid token
    token = generate_test_token()
    
    response = client.get(
        "/protected",
        headers={
            "Authorization": f"Bearer {token}",
            "x-phlow-agent-id": "test-agent"
        }
    )
    assert response.status_code == 200
```

## Performance Optimizations

### Async Batching

```python
class PhlowMiddleware:
    async def authenticate_batch(
        self, 
        requests: List[Tuple[str, str]]  # [(token, agent_id), ...]
    ) -> List[PhlowContext]:
        """Batch authentication for multiple requests."""
        
        # Extract unique agent IDs
        agent_ids = list(set(agent_id for _, agent_id in requests))
        
        # Batch fetch agent cards
        agent_cards = await self.supabase_helpers.get_agent_cards_batch(agent_ids)
        agent_card_map = {card.agent_id: card for card in agent_cards}
        
        # Process all tokens in parallel
        tasks = []
        for token, agent_id in requests:
            agent_card = agent_card_map.get(agent_id)
            if agent_card:
                task = verify_token(token, agent_card.public_key)
                tasks.append((task, agent_card, token))
        
        results = await asyncio.gather(*[task for task, _, _ in tasks])
        
        # Build contexts
        contexts = []
        for i, (claims, agent_card, token) in enumerate(
            zip(results, [item[1] for item in tasks], [item[2] for item in tasks])
        ):
            contexts.append(PhlowContext(
                agent=agent_card,
                token=token,
                claims=claims,
                supabase=self.supabase
            ))
        
        return contexts
```

## Deployment Considerations

### Environment Configuration

```python
# Production configuration example
import os
from phlow import PhlowConfig, AgentCard, RateLimitConfig, AuditConfig

def create_production_config() -> PhlowConfig:
    return PhlowConfig(
        supabase_url=os.getenv("SUPABASE_URL"),
        supabase_anon_key=os.getenv("SUPABASE_ANON_KEY"),
        agent_card=AgentCard(
            agent_id=os.getenv("AGENT_ID"),
            name=os.getenv("AGENT_NAME"),
            public_key=os.getenv("AGENT_PUBLIC_KEY"),
            permissions=os.getenv("AGENT_PERMISSIONS", "").split(",")
        ),
        private_key=os.getenv("AGENT_PRIVATE_KEY"),
        token_expiry=os.getenv("TOKEN_EXPIRY", "1h"),
        rate_limiting=RateLimitConfig(
            max_requests=int(os.getenv("RATE_LIMIT_MAX", "1000")),
            window_seconds=int(os.getenv("RATE_LIMIT_WINDOW", "3600"))
        ),
        audit_config=AuditConfig(
            enabled=os.getenv("AUDIT_ENABLED", "true").lower() == "true",
            log_level=os.getenv("AUDIT_LOG_LEVEL", "INFO")
        )
    )
```

---

This Python implementation provides a comprehensive, production-ready authentication system with modern Python patterns, extensive type safety, and framework integrations. The next section covers the [Database Schema](database-schema.md) that powers the agent registry.