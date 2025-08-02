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


# Production token operations
def generate_token(agent_card: AgentCard, private_key: str) -> str:
    """Generate a JWT token for the agent.

    Args:
        agent_card: Agent card containing identity information
        private_key: Private key for signing (PEM format for RS256, string for HS256)

    Returns:
        Signed JWT token

    Raises:
        ValueError: If required parameters are missing
        Exception: If token generation fails
    """
    from datetime import datetime, timedelta, timezone

    import jwt

    if not agent_card or not private_key:
        raise ValueError("agent_card and private_key are required")

    # Generate payload with required and optional claims
    payload = {
        "sub": agent_card.metadata.get("agent_id") if agent_card.metadata else None,
        "name": agent_card.name,
        "iat": datetime.now(timezone.utc),
        "exp": datetime.now(timezone.utc) + timedelta(hours=1),
        "iss": agent_card.service_url or agent_card.name,
        "skills": agent_card.skills,
    }

    # Remove None values
    payload = {k: v for k, v in payload.items() if v is not None}

    # Determine algorithm based on key format
    algorithm = "RS256" if private_key.startswith("-----BEGIN") else "HS256"

    return jwt.encode(payload, private_key, algorithm=algorithm)


def verify_token(token: str, public_key: str) -> dict:
    """Verify a JWT token.

    Args:
        token: JWT token to verify
        public_key: Public key for verification (PEM format for RS256, string for HS256)

    Returns:
        Decoded token payload

    Raises:
        TokenError: If token verification fails
    """
    import jwt

    if not token or not public_key:
        raise TokenError("token and public_key are required")

    try:
        # Determine algorithm from token header for security
        unverified_header = jwt.get_unverified_header(token)
        algorithm = unverified_header.get("alg", "HS256")

        # Validate algorithm matches key type
        if algorithm == "RS256" and not public_key.startswith("-----BEGIN"):
            raise TokenError("RS256 algorithm requires PEM-formatted public key")
        elif algorithm == "HS256" and public_key.startswith("-----BEGIN"):
            raise TokenError("HS256 algorithm requires string key, not PEM format")

        # Verify token with signature validation and required claims
        decoded = jwt.decode(
            token,
            public_key,
            algorithms=[algorithm],
            options={"verify_signature": True, "require": ["exp", "iat"]},
        )

        return decoded

    except jwt.ExpiredSignatureError:
        raise TokenError("Token has expired")
    except jwt.InvalidSignatureError:
        raise TokenError("Invalid token signature")
    except jwt.InvalidTokenError as e:
        raise TokenError(f"Invalid token: {str(e)}")


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
