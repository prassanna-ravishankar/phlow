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

# RBAC exports
from .rbac import (
    RoleCache,
    RoleCredential,
    RoleCredentialStore,
    RoleCredentialVerifier,
    VerifiablePresentation,
)
from .supabase_helpers import SupabaseHelpers
from .types import AgentCard, AuditLog, PhlowConfig, PhlowContext, VerifyOptions


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
    # Core middleware and types
    "PhlowMiddleware",
    "PhlowConfig",
    "PhlowContext",
    "VerifyOptions",
    "AuditLog",
    "AgentCard",

    # Exceptions
    "PhlowError",
    "AuthenticationError",
    "AuthorizationError",
    "ConfigurationError",
    "TokenError",
    "RateLimitError",

    # Helpers
    "SupabaseHelpers",

    # RBAC components
    "RoleCredential",
    "VerifiablePresentation",
    "RoleCredentialVerifier",
    "RoleCache",
    "RoleCredentialStore",

    # Utility functions
    "generate_token",
    "verify_token",
]
