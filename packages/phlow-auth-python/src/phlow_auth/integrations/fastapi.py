"""FastAPI integration for Phlow authentication."""

from functools import wraps
from typing import Callable, List, Optional

try:
    from fastapi import Depends, HTTPException, Request
    from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
except ImportError:
    raise ImportError(
        "FastAPI is required for this integration. Install with: pip install fastapi"
    )

from ..exceptions import PhlowError
from ..middleware import PhlowMiddleware
from ..types import PhlowContext, VerifyOptions


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
        required_permissions: Optional[List[str]] = None,
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
            credentials: Optional[HTTPAuthorizationCredentials] = Depends(
                self.security
            ),
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
                options = VerifyOptions(
                    required_permissions=required_permissions,
                    allow_expired=allow_expired,
                )

                context = await self.middleware.authenticate(
                    credentials.credentials, agent_id, options
                )

                return context

            except PhlowError as e:
                raise HTTPException(
                    status_code=e.status_code,
                    detail={"error": e.code, "message": e.message},
                )

        return auth_dependency

    def require_auth(
        self,
        required_permissions: Optional[List[str]] = None,
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
            auth_dep = self.create_auth_dependency(required_permissions, allow_expired)

            # Add auth dependency to function signature
            func.__annotations__["phlow_context"] = PhlowContext

            @wraps(func)
            async def wrapper(*args, **kwargs):  # type: ignore
                # FastAPI will inject the auth dependency
                return await func(*args, **kwargs)

            # Inject dependency
            wrapper.__annotations__ = func.__annotations__.copy()
            wrapper = Depends(auth_dep)(wrapper)

            return wrapper

        return decorator


def create_phlow_dependency(
    middleware: PhlowMiddleware,
    required_permissions: Optional[List[str]] = None,
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
