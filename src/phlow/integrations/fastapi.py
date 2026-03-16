"""FastAPI integration for Phlow authentication."""

from collections.abc import Callable
from typing import Any

try:
    from fastapi import Depends, FastAPI, HTTPException, Request
    from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
except ImportError:
    raise ImportError(
        "FastAPI is required for this integration. Install with: pip install phlow[fastapi]"
    )

from ..exceptions import PhlowError
from ..middleware import PhlowMiddleware
from ..types import PhlowContext


class FastAPIPhlowAuth:
    """FastAPI integration for Phlow authentication."""

    def __init__(self, middleware: PhlowMiddleware):
        """Initialize FastAPI integration.

        Args:
            middleware: Phlow middleware instance
        """
        self.middleware = middleware
        self.security = HTTPBearer(auto_error=False)

    def create_auth_dependency(
        self,
        required_permissions: list[str] | None = None,
    ) -> Callable:
        """Create FastAPI dependency for authentication.

        Args:
            required_permissions: Required permissions for access

        Returns:
            FastAPI dependency function
        """

        async def auth_dependency(
            credentials: HTTPAuthorizationCredentials | None = Depends(self.security),
        ) -> PhlowContext:
            if not credentials:
                raise HTTPException(
                    status_code=401,
                    detail="Authorization header required",
                    headers={"WWW-Authenticate": "Bearer"},
                )

            try:
                context = self.middleware.verify_token(credentials.credentials)

                if required_permissions:
                    agent_permissions = (
                        context.agent.metadata.get("permissions", [])
                        if context.agent.metadata
                        else []
                    )
                    # Also check permissions from JWT claims
                    claim_permissions = context.claims.get("permissions", [])
                    all_permissions = set(agent_permissions) | set(claim_permissions)

                    for permission in required_permissions:
                        if permission not in all_permissions:
                            raise HTTPException(
                                status_code=403,
                                detail={
                                    "error": "PERMISSION_DENIED",
                                    "message": f"Agent lacks required permission: {permission}",
                                },
                            )

                return context

            except PhlowError as e:
                raise HTTPException(
                    status_code=e.status_code,
                    detail={"error": e.code, "message": e.message},
                )

        return auth_dependency

    def setup_agent_card_route(self, app: FastAPI) -> None:
        """Register the A2A agent card discovery endpoint.

        Adds GET /.well-known/agent.json to the FastAPI app, serving
        the agent card from middleware config. Every A2A agent needs this.

        Args:
            app: FastAPI application instance
        """
        agent_card = self.middleware.config.agent_card

        @app.get("/.well-known/agent.json")
        def get_agent_card() -> dict[str, Any]:
            card: dict[str, Any] = {
                "name": agent_card.name,
                "description": agent_card.description,
                "version": agent_card.schema_version,
                "capabilities": dict.fromkeys(agent_card.skills, True),
                "input_modes": ["text"],
                "output_modes": ["text"],
                "endpoints": {"task": "/tasks/send"},
            }
            if agent_card.metadata:
                card["id"] = agent_card.metadata.get("agent_id")
                card["metadata"] = agent_card.metadata
            if agent_card.service_url:
                card["url"] = agent_card.service_url
            return card

    def create_role_auth_dependency(
        self,
        required_role: str,
        allow_expired: bool = False,
    ) -> Callable:
        """Create FastAPI dependency for role-based authentication.

        Args:
            required_role: Role required for access
            allow_expired: Whether to allow expired tokens

        Returns:
            FastAPI dependency function
        """

        async def role_auth_dependency(
            request: Request,
            credentials: HTTPAuthorizationCredentials | None = Depends(self.security),
        ) -> PhlowContext:
            if not credentials:
                raise HTTPException(
                    status_code=401,
                    detail="Authorization header required",
                    headers={"WWW-Authenticate": "Bearer"},
                )

            try:
                # Use the role-based authentication from middleware
                context = await self.middleware.authenticate_with_role(
                    credentials.credentials, required_role
                )

                return context

            except PhlowError as e:
                raise HTTPException(
                    status_code=e.status_code,
                    detail={"error": e.code, "message": e.message},
                )
            except Exception as e:
                raise HTTPException(
                    status_code=401,
                    detail=f"Role authentication failed: {str(e)}",
                )

        return role_auth_dependency


def create_phlow_dependency(
    middleware: PhlowMiddleware,
    required_permissions: list[str] | None = None,
) -> Callable:
    """Create a FastAPI dependency for Phlow authentication.

    Args:
        middleware: Phlow middleware instance
        required_permissions: Required permissions for access

    Returns:
        FastAPI dependency function
    """
    integration = FastAPIPhlowAuth(middleware)
    return integration.create_auth_dependency(required_permissions)


def create_phlow_role_dependency(
    middleware: PhlowMiddleware,
    required_role: str,
) -> Callable:
    """Create a FastAPI dependency for Phlow role-based authentication.

    Args:
        middleware: Phlow middleware instance
        required_role: Role required for access

    Returns:
        FastAPI dependency function
    """
    integration = FastAPIPhlowAuth(middleware)
    return integration.create_role_auth_dependency(required_role)


# Convenience aliases for easier usage
def phlow_auth(
    middleware: PhlowMiddleware,
    required_permissions: list[str] | None = None,
) -> Callable:
    """Convenience function for permission-based authentication dependency."""
    return create_phlow_dependency(middleware, required_permissions)


def phlow_auth_role(
    middleware: PhlowMiddleware,
    required_role: str,
) -> Callable:
    """Convenience function for role-based authentication dependency."""
    return create_phlow_role_dependency(middleware, required_role)
