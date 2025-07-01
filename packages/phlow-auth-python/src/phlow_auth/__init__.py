"""Phlow Authentication Library for Python.

Agent-to-Agent (A2A) authentication framework with Supabase integration.
"""

from .middleware import PhlowMiddleware
from .jwt_utils import generate_token, verify_token, decode_token, is_token_expired
from .types import AgentCard, PhlowConfig, JWTClaims, PhlowContext
from .exceptions import (
    PhlowError,
    AuthenticationError,
    AuthorizationError,
    ConfigurationError,
    TokenError,
    RateLimitError,
)
from .supabase_helpers import SupabaseHelpers

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