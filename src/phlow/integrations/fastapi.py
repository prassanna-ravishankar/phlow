"""FastAPI integration for Phlow authentication."""

from collections.abc import Callable

try:
    from fastapi import Depends, HTTPException, Request
    from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
except ImportError:
    raise ImportError(
        "FastAPI is required for this integration. Install with: pip install fastapi"
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
        allow_expired: bool = False,
    ) -> Callable:
        """Create FastAPI dependency for authentication.

        Args:
            required_permissions: Required permissions for access
            allow_expired: Whether to allow expired tokens

        Returns:
            FastAPI dependency function
        """

        async def auth_dependency(
            request: Request,
            credentials: HTTPAuthorizationCredentials | None = Depends(self.security),
        ) -> PhlowContext:
            if not credentials:
                raise HTTPException(
                    status_code=401,
                    detail="Authorization header required",
                    headers={"WWW-Authenticate": "Bearer"},
                )

            # Extract agent ID from headers
            agent_id = request.headers.get("x-phlow-agent-id") or request.headers.get(
                "X-Phlow-Agent-Id"
            )
            if not agent_id:
                raise HTTPException(
                    status_code=401, detail="X-Phlow-Agent-Id header required"
                )

            try:
                # Use the verify_token method for standard authentication
                context = self.middleware.verify_token(credentials.credentials)

                # TODO: Add permission checking logic here if needed
                if required_permissions:
                    # For now, just log that permissions were requested
                    # In a full implementation, you'd check context.agent permissions
                    pass

                return context

            except PhlowError as e:
                raise HTTPException(
                    status_code=e.status_code,
                    detail={"error": e.code, "message": e.message},
                )

        return auth_dependency

    def require_auth(
        self,
        required_permissions: list[str] | None = None,
        allow_expired: bool = False,
    ) -> Callable:
        """Decorator for protecting FastAPI routes.

        Args:
            required_permissions: Required permissions for access
            allow_expired: Whether to allow expired tokens

        Returns:
            Decorator function
        """

        def decorator(func: Callable) -> Callable:
            # For FastAPI, decorators are complex. It's better to use the dependency directly.
            # This decorator just returns the original function with a note that
            # the user should manually add the dependency to their endpoint.

            # Add hints to the function for documentation
            if not hasattr(func, '__phlow_required_permissions__'):
                func.__phlow_required_permissions__ = required_permissions  # type: ignore

            return func

        return decorator

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

    def require_role(
        self,
        required_role: str,
        allow_expired: bool = False,
    ) -> Callable:
        """Decorator for protecting FastAPI routes with role requirements.

        Args:
            required_role: Role required for access
            allow_expired: Whether to allow expired tokens

        Returns:
            Decorator function
        """

        def decorator(func: Callable) -> Callable:
            # For FastAPI, decorators are complex. It's better to use the dependency directly.
            # This decorator just returns the original function with a note that
            # the user should manually add the dependency to their endpoint.

            # Add a hint to the function for documentation
            if not hasattr(func, '__phlow_required_role__'):
                func.__phlow_required_role__ = required_role  # type: ignore

            return func

        return decorator


def create_phlow_dependency(
    middleware: PhlowMiddleware,
    required_permissions: list[str] | None = None,
    allow_expired: bool = False,
) -> Callable:
    """Create a FastAPI dependency for Phlow authentication.

    Args:
        middleware: Phlow middleware instance
        required_permissions: Required permissions for access
        allow_expired: Whether to allow expired tokens

    Returns:
        FastAPI dependency function
    """
    integration = FastAPIPhlowAuth(middleware)
    return integration.create_auth_dependency(required_permissions, allow_expired)


def create_phlow_role_dependency(
    middleware: PhlowMiddleware,
    required_role: str,
    allow_expired: bool = False,
) -> Callable:
    """Create a FastAPI dependency for Phlow role-based authentication.

    Args:
        middleware: Phlow middleware instance
        required_role: Role required for access
        allow_expired: Whether to allow expired tokens

    Returns:
        FastAPI dependency function
    """
    integration = FastAPIPhlowAuth(middleware)
    return integration.create_role_auth_dependency(required_role, allow_expired)


# Convenience aliases for easier usage
def phlow_auth(
    middleware: PhlowMiddleware,
    required_permissions: list[str] | None = None,
    allow_expired: bool = False,
) -> Callable:
    """Convenience function for permission-based authentication dependency."""
    return create_phlow_dependency(middleware, required_permissions, allow_expired)


def phlow_auth_role(
    middleware: PhlowMiddleware,
    required_role: str,
    allow_expired: bool = False,
) -> Callable:
    """Convenience function for role-based authentication dependency."""
    return create_phlow_role_dependency(middleware, required_role, allow_expired)
