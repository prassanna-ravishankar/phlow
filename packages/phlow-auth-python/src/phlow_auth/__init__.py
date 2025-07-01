"""Phlow Authentication Library for Python.

Agent-to-Agent (A2A) authentication framework with Supabase integration.
"""

from .exceptions import (
    AuthenticationError,
    AuthorizationError,
    ConfigurationError,
    PhlowError,
    RateLimitError,
    TokenError,
)
from .jwt_utils import decode_token, generate_token, is_token_expired, verify_token
from .middleware import PhlowMiddleware
from .supabase_helpers import SupabaseHelpers
from .types import AgentCard, JWTClaims, PhlowConfig, PhlowContext

__version__ = "0.1.0"
__all__ = [
    "PhlowMiddleware",
    "generate_token",
    "verify_token",
    "decode_token",
    "is_token_expired",
    "AgentCard",
    "PhlowConfig",
    "JWTClaims",
    "PhlowContext",
    "PhlowError",
    "AuthenticationError",
    "AuthorizationError",
    "ConfigurationError",
    "TokenError",
    "RateLimitError",
    "SupabaseHelpers",
]
