"""Type definitions for Phlow authentication."""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from pydantic import BaseModel


class AgentCard(BaseModel):
    """Agent card containing identification and permission information."""

    agent_id: str
    name: str
    description: Optional[str] = None
    permissions: List[str] = []
    public_key: str
    endpoints: Optional[Dict[str, str]] = None
    metadata: Optional[Dict[str, Any]] = None


class PhlowConfig(BaseModel):
    """Configuration for Phlow middleware."""

    supabase_url: str
    supabase_anon_key: str
    agent_card: AgentCard
    private_key: str
    token_expiry: str = "1h"
    refresh_threshold: int = 300  # seconds
    enable_audit: bool = False
    rate_limiting: Optional[Dict[str, int]] = None


class JWTClaims(BaseModel):
    """JWT token claims."""

    sub: str  # subject (agent ID)
    iss: str  # issuer (agent ID)
    aud: str  # audience (target agent ID)
    exp: int  # expiration time
    iat: int  # issued at
    permissions: List[str] = []
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class PhlowContext:
    """Context information for authenticated requests."""

    agent: AgentCard
    token: str
    claims: JWTClaims
    supabase: Any  # supabase client


class VerifyOptions(BaseModel):
    """Options for token verification."""

    required_permissions: Optional[List[str]] = None
    allow_expired: bool = False


class AuditLog(BaseModel):
    """Audit log entry."""

    timestamp: str
    event: str
    agent_id: str
    target_agent_id: Optional[str] = None
    details: Optional[Dict[str, Any]] = None
