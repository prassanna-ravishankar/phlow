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
from .types import PhlowConfig, PhlowContext, VerifyOptions, AuditLog

# Re-export useful A2A types for convenience
from a2a_sdk import (
    AgentCard as A2AAgentCard,
    A2AContext,
    A2AServer,
    A2AClient,
    Task,
    Message,
)

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
    # A2A re-exports
    "A2AAgentCard",
    "A2AContext",
    "A2AServer",
    "A2AClient",
    "Task",
    "Message",
]