"""Phlow Authentication Library for Python.

A2A Protocol extension with Supabase integration for enhanced agent authentication.
"""

from .exceptions import (
    AuthenticationError,
    AuthorizationError,
    ConfigurationError,
    PhlowError,
    RateLimitError,
    TokenError,
)
from .middleware import PhlowMiddleware
from .supabase_helpers import SupabaseHelpers
from .types import PhlowConfig, PhlowContext, VerifyOptions, AuditLog, AgentCard

# Placeholder functions for token operations
def generate_token(agent_card: AgentCard, private_key: str) -> str:
    """Generate a JWT token for the agent."""
    # This would use PyJWT in real implementation
    return "mock-token"

def verify_token(token: str, public_key: str) -> dict:
    """Verify a JWT token."""
    # This would use PyJWT in real implementation
    return {"sub": "agent-id", "exp": 1234567890}

__version__ = "0.1.0"
__all__ = [
    "PhlowMiddleware",
    "PhlowConfig",
    "PhlowContext",
    "VerifyOptions",
    "AuditLog",
    "PhlowError",
    "AuthenticationError",
    "AuthorizationError",
    "ConfigurationError",
    "TokenError",
    "RateLimitError",
    "SupabaseHelpers",
    "AgentCard",
    "generate_token",
    "verify_token",
]