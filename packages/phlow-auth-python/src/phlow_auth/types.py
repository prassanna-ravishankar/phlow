"""Type definitions for Phlow authentication."""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel
from supabase import Client as SupabaseClient
from typing_extensions import TypedDict

try:
    from a2a.client import A2AClient
    from a2a.types import AgentCard as A2AAgentCard
except ImportError:
    A2AClient = None
    A2AAgentCard = None


# AgentCard type definition (A2A-compliant)
class AgentCard(BaseModel):
    """A2A-compliant Agent Card."""

    schema_version: str = "1.0"
    name: str
    description: str = ""
    service_url: str = ""
    skills: List[str] = []
    security_schemes: Dict[str, Any] = {}
    metadata: Optional[Dict[str, Any]] = None


class RateLimitingConfig(TypedDict):
    """Rate limiting configuration."""

    max_requests: int
    window_ms: int


class PhlowConfig(BaseModel):
    """Phlow configuration."""

    # Supabase configuration
    supabase_url: str
    supabase_anon_key: str

    # Agent configuration (A2A-compliant)
    agent_card: AgentCard
    private_key: str
    public_key: Optional[str] = None

    # Phlow-specific options
    enable_audit_log: bool = False
    enable_rate_limiting: bool = False
    rate_limit_config: Optional[RateLimitingConfig] = None


class PhlowContext(BaseModel):
    """Authentication context with Phlow extensions."""

    # From A2A authentication
    agent: AgentCard
    token: str
    claims: Dict[str, Any]

    # Phlow additions
    supabase: SupabaseClient
    a2a_client: Optional[Any] = None  # A2AClient when available

    model_config = {"arbitrary_types_allowed": True}


class VerifyOptions(BaseModel):
    """Options for token verification (kept for backward compatibility)."""

    required_permissions: Optional[List[str]] = None
    allow_expired: bool = False


# Supabase-specific types
class SupabaseAgentRecord(TypedDict):
    """Agent record in Supabase."""

    agent_id: str
    name: str
    description: Optional[str]
    service_url: Optional[str]
    schema_version: str
    skills: List[Dict[str, Any]]
    security_schemes: Dict[str, Any]
    public_key: str
    metadata: Optional[Dict[str, Any]]
    created_at: str
    updated_at: Optional[str]


class AuthAuditLog(TypedDict):
    """Authentication audit log entry."""

    id: Optional[str]
    agent_id: str
    timestamp: str
    event_type: str  # 'authentication', 'authorization', 'rate_limit'
    success: bool
    metadata: Optional[Dict[str, Any]]
    error_code: Optional[str]
    error_message: Optional[str]


class AuditLog(BaseModel):
    """Audit log entry (kept for backward compatibility)."""

    timestamp: str
    event: str
    agent_id: str
    target_agent_id: Optional[str] = None
    details: Optional[Dict[str, Any]] = None
