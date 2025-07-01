"""JWT utilities for Phlow authentication."""

import re
import time
from typing import Optional

import jwt
from cryptography.hazmat.primitives import serialization

from .exceptions import TokenError
from .types import AgentCard, JWTClaims


def generate_token(
    agent_card: AgentCard, private_key: str, audience: str, expires_in: str = "1h"
) -> str:
    """Generate a JWT token for agent authentication.

    Args:
        agent_card: The agent card containing agent information
        private_key: The private key to sign the token
        audience: The target agent ID
        expires_in: Token expiration time (e.g., "1h", "30m", "3600s")

    Returns:
        The generated JWT token

    Raises:
        TokenError: If token generation fails
    """
    try:
        now = int(time.time())
        expiry_seconds = _parse_expiry(expires_in)

        claims = {
            "sub": agent_card.agent_id,
            "iss": agent_card.agent_id,
            "aud": audience,
            "exp": now + expiry_seconds,
            "iat": now,
            "permissions": agent_card.permissions,
            "metadata": agent_card.metadata,
        }

        # Load private key
        private_key_obj = serialization.load_pem_private_key(
            private_key.encode("utf-8"), password=None
        )

        token = jwt.encode(claims, private_key_obj, algorithm="RS256")
        return token

    except Exception as e:
        raise TokenError(
            f"Failed to generate token: {str(e)}", "TOKEN_GENERATION_FAILED"
        )


def verify_token(
    token: str,
    public_key: str,
    audience: Optional[str] = None,
    issuer: Optional[str] = None,
    ignore_expiration: bool = False,
) -> JWTClaims:
    """Verify a JWT token.

    Args:
        token: The JWT token to verify
        public_key: The public key to verify the signature
        audience: Expected audience (optional)
        issuer: Expected issuer (optional)
        ignore_expiration: Whether to ignore token expiration

    Returns:
        The verified JWT claims

    Raises:
        TokenError: If token verification fails
    """
    try:
        # Load public key
        public_key_obj = serialization.load_pem_public_key(public_key.encode("utf-8"))

        options = {"verify_exp": not ignore_expiration}

        decoded = jwt.decode(
            token,
            public_key_obj,
            algorithms=["RS256"],
            audience=audience,
            issuer=issuer,
            options=options,
        )

        return JWTClaims(**decoded)

    except jwt.ExpiredSignatureError:
        raise TokenError("Token has expired", "TOKEN_EXPIRED")
    except jwt.InvalidTokenError as e:
        raise TokenError(f"Invalid token: {str(e)}", "TOKEN_INVALID")
    except Exception as e:
        raise TokenError(f"Token verification failed: {str(e)}", "TOKEN_VERIFY_FAILED")


def decode_token(token: str) -> Optional[JWTClaims]:
    """Decode a JWT token without verification.

    Args:
        token: The JWT token to decode

    Returns:
        The decoded JWT claims or None if decoding fails
    """
    try:
        decoded = jwt.decode(token, options={"verify_signature": False})
        return JWTClaims(**decoded)
    except Exception:
        return None


def is_token_expired(token: str, threshold_seconds: int = 0) -> bool:
    """Check if a token is expired or will expire within the threshold.

    Args:
        token: The JWT token to check
        threshold_seconds: Additional time buffer (default: 0)

    Returns:
        True if the token is expired or will expire within threshold
    """
    decoded = decode_token(token)
    if not decoded or not decoded.exp:
        return True

    now = int(time.time())
    return decoded.exp - now <= threshold_seconds


def _parse_expiry(expiry: str) -> int:
    """Parse expiry string to seconds.

    Args:
        expiry: Expiry string (e.g., "1h", "30m", "3600s")

    Returns:
        Number of seconds

    Raises:
        ValueError: If expiry format is invalid
    """
    match = re.match(r"^(\d+)([smhd])$", expiry)
    if not match:
        raise ValueError(f"Invalid expiry format: {expiry}")

    value, unit = match.groups()
    value = int(value)

    multipliers = {
        "s": 1,
        "m": 60,
        "h": 60 * 60,
        "d": 60 * 60 * 24,
    }

    return value * multipliers[unit]
