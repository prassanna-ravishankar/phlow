"""Type definitions for Phlow authentication."""

from typing import Any, Dict, List, Optional, TypedDict
from pydantic import BaseModel
from a2a_sdk import AgentCard as A2AAgentCard
from supabase import Client as SupabaseClient


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
    agent_card: A2AAgentCard
    private_key: str
    
    # Phlow-specific options
    enable_audit: bool = False
    rate_limiting: Optional[RateLimitingConfig] = None
    refresh_threshold: int = 300  # seconds


class PhlowContext(BaseModel):
    """Authentication context with Phlow extensions."""
    
    # From A2A authentication
    agent: A2AAgentCard
    token: str
    claims: Dict[str, Any]
    
    # Phlow additions
    supabase: SupabaseClient
    
    class Config:
        """Pydantic configuration."""
        
        arbitrary_types_allowed = True


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