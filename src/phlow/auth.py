"""Lightweight JWT authentication for A2A agents.

PhlowAuth provides JWT verification without requiring Supabase or any
external dependencies. Use this when you just need auth, not the full
middleware stack.

Usage:
    auth = PhlowAuth(private_key="your-secret")
    token = auth.create_token(agent_id="my-agent", name="My Agent")
    claims = auth.verify(token)
"""

from datetime import datetime, timedelta, timezone
from typing import Any

import jwt

from .exceptions import AuthenticationError
from .types import AgentCard


class PhlowAuth:
    """Lightweight JWT authentication for A2A agents.

    Works without Supabase. Handles token creation and verification
    with HS256 (shared secret) or RS256 (key pair) algorithms.
    """

    def __init__(
        self,
        private_key: str,
        public_key: str | None = None,
        algorithm: str | None = None,
        token_expiry_hours: float = 1.0,
    ):
        """Initialize auth with signing keys.

        Args:
            private_key: Secret key for HS256, or PEM private key for RS256
            public_key: PEM public key for RS256 verification (not needed for HS256)
            algorithm: Force a specific algorithm ("HS256" or "RS256").
                      Auto-detected from key format if not specified.
            token_expiry_hours: Default token lifetime in hours
        """
        if not private_key:
            raise ValueError("private_key is required")

        self.private_key = private_key
        self.public_key = public_key
        self.token_expiry_hours = token_expiry_hours

        if algorithm:
            if algorithm not in ("HS256", "RS256"):
                raise ValueError(
                    f"Unsupported algorithm: {algorithm}. Use 'HS256' or 'RS256'."
                )
            self.algorithm = algorithm
        else:
            self.algorithm = (
                "RS256" if private_key.strip().startswith("-----BEGIN") else "HS256"
            )

    def create_token(
        self,
        agent_id: str | None = None,
        name: str | None = None,
        permissions: list[str] | None = None,
        extra_claims: dict[str, Any] | None = None,
        expiry_hours: float | None = None,
    ) -> str:
        """Create a signed JWT token.

        Args:
            agent_id: Agent identifier (becomes the 'sub' claim)
            name: Agent name
            permissions: List of permission strings
            extra_claims: Additional JWT claims to include
            expiry_hours: Override default token lifetime

        Returns:
            Signed JWT token string
        """
        hours = expiry_hours if expiry_hours is not None else self.token_expiry_hours
        now = datetime.now(timezone.utc)

        payload: dict[str, Any] = {
            "iat": now,
            "exp": now + timedelta(hours=hours),
        }

        if agent_id is not None:
            payload["sub"] = agent_id
        if name is not None:
            payload["name"] = name
        if permissions:
            payload["permissions"] = permissions
        if extra_claims:
            payload.update(extra_claims)

        return jwt.encode(payload, self.private_key, algorithm=self.algorithm)

    def create_token_for_agent(self, agent_card: AgentCard) -> str:
        """Create a signed JWT from an AgentCard.

        Args:
            agent_card: Agent card to create token for

        Returns:
            Signed JWT token string
        """
        agent_id = agent_card.metadata.get("agent_id") if agent_card.metadata else None
        return self.create_token(
            agent_id=agent_id,
            name=agent_card.name,
            permissions=agent_card.permissions or None,
            extra_claims={"skills": agent_card.skills} if agent_card.skills else None,
        )

    def verify(self, token: str) -> dict[str, Any]:
        """Verify a JWT token and return its claims.

        Args:
            token: JWT token to verify

        Returns:
            Decoded claims dictionary

        Raises:
            AuthenticationError: If verification fails
        """
        if not token or not isinstance(token, str):
            raise AuthenticationError("Token must be a non-empty string")

        if len(token) > 8192:
            raise AuthenticationError("Token exceeds maximum length")

        verification_key = self._get_verification_key(token)

        try:
            return jwt.decode(
                token,
                verification_key,
                algorithms=[self.algorithm],
                options={"verify_signature": True, "require": ["exp", "iat"]},
            )
        except jwt.ExpiredSignatureError:
            raise AuthenticationError("Token has expired")
        except jwt.InvalidSignatureError:
            raise AuthenticationError("Invalid token signature")
        except jwt.InvalidTokenError as e:
            raise AuthenticationError(f"Invalid token: {e}")

    def create_fastapi_dependency(
        self,
        required_permissions: list[str] | None = None,
    ):
        """Create a FastAPI dependency for JWT authentication.

        No Supabase required. Returns decoded claims dict (not PhlowContext).

        Usage:
            auth = PhlowAuth(private_key="secret")
            auth_required = auth.create_fastapi_dependency()

            @app.get("/protected")
            async def protected(claims: dict = Depends(auth_required)):
                return {"agent": claims.get("sub")}

        Args:
            required_permissions: Permissions the token must contain

        Returns:
            FastAPI dependency function
        """
        try:
            from fastapi import Depends, HTTPException
            from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
        except ImportError:
            raise ImportError(
                "FastAPI is required for this feature. Install with: pip install phlow[fastapi]"
            )

        security = HTTPBearer(auto_error=False)

        async def dependency(
            credentials: HTTPAuthorizationCredentials | None = Depends(security),
        ) -> dict[str, Any]:
            if not credentials:
                raise HTTPException(
                    status_code=401,
                    detail="Authorization header required",
                    headers={"WWW-Authenticate": "Bearer"},
                )

            try:
                claims = self.verify(credentials.credentials)
            except AuthenticationError as e:
                raise HTTPException(status_code=401, detail=str(e))

            if required_permissions:
                token_permissions = set(claims.get("permissions", []))
                for perm in required_permissions:
                    if perm not in token_permissions:
                        raise HTTPException(
                            status_code=403,
                            detail=f"Missing required permission: {perm}",
                        )

            return claims

        return dependency

    def _get_verification_key(self, token: str) -> str:
        """Get the appropriate key for verification."""
        if self.algorithm == "RS256":
            if not self.public_key:
                raise AuthenticationError("Public key required for RS256 verification")
            return self.public_key
        return self.private_key
