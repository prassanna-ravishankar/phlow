"""Tests for RBAC FastAPI integration."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from phlow.exceptions import AuthenticationError


class TestFastAPIRBACIntegration:
    """Test RBAC integration with FastAPI."""

    @pytest.fixture
    def mock_middleware(self):
        """Create mock PhlowMiddleware."""
        middleware = MagicMock()
        middleware.authenticate_with_role = AsyncMock()
        return middleware

    @pytest.fixture
    def fastapi_auth(self, mock_middleware):
        """Create FastAPIPhlowAuth instance."""
        # Import here to avoid import errors if FastAPI not installed
        try:
            from phlow.integrations.fastapi import FastAPIPhlowAuth
            return FastAPIPhlowAuth(mock_middleware)
        except ImportError:
            pytest.skip("FastAPI not installed")

    @pytest.fixture
    def mock_request(self):
        """Create mock FastAPI request."""
        request = MagicMock()
        return request

    @pytest.fixture
    def mock_credentials(self):
        """Create mock HTTPAuthorizationCredentials."""
        credentials = MagicMock()
        credentials.credentials = "test-token"
        return credentials

    @pytest.mark.asyncio
    async def test_create_role_auth_dependency_success(self, fastapi_auth, mock_middleware, mock_request, mock_credentials):
        """Test successful role authentication dependency."""
        # Mock successful authentication
        mock_context = MagicMock()
        mock_context.verified_roles = ["admin"]
        mock_middleware.authenticate_with_role.return_value = mock_context

        # Create dependency function
        auth_dep = fastapi_auth.create_role_auth_dependency("admin")

        # Call the dependency
        context = await auth_dep(mock_request, mock_credentials)

        assert context == mock_context
        mock_middleware.authenticate_with_role.assert_called_once_with("test-token", "admin")

    @pytest.mark.asyncio
    async def test_create_role_auth_dependency_no_credentials(self, fastapi_auth, mock_request):
        """Test role authentication dependency with no credentials."""
        try:
            from fastapi import HTTPException
        except ImportError:
            pytest.skip("FastAPI not installed")

        # Create dependency function
        auth_dep = fastapi_auth.create_role_auth_dependency("admin")

        # Call the dependency with no credentials
        with pytest.raises(HTTPException) as exc_info:
            await auth_dep(mock_request, None)

        assert exc_info.value.status_code == 401
        assert "Authorization header required" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_create_role_auth_dependency_auth_error(self, fastapi_auth, mock_middleware, mock_request, mock_credentials):
        """Test role authentication dependency with authentication error."""
        try:
            from fastapi import HTTPException
        except ImportError:
            pytest.skip("FastAPI not installed")

        # Mock authentication failure
        mock_middleware.authenticate_with_role.side_effect = AuthenticationError("Role not verified")

        # Create dependency function
        auth_dep = fastapi_auth.create_role_auth_dependency("admin")

        # Call the dependency
        with pytest.raises(HTTPException) as exc_info:
            await auth_dep(mock_request, mock_credentials)

        assert exc_info.value.status_code == 401
        # AuthenticationError is a PhlowError, so it returns structured error
        assert exc_info.value.detail["error"] == "AUTH_ERROR"
        assert exc_info.value.detail["message"] == "Role not verified"

    @pytest.mark.asyncio
    async def test_create_role_auth_dependency_generic_error(self, fastapi_auth, mock_middleware, mock_request, mock_credentials):
        """Test role authentication dependency with generic error."""
        try:
            from fastapi import HTTPException
        except ImportError:
            pytest.skip("FastAPI not installed")

        # Mock generic exception
        mock_middleware.authenticate_with_role.side_effect = Exception("Something went wrong")

        # Create dependency function
        auth_dep = fastapi_auth.create_role_auth_dependency("admin")

        # Call the dependency
        with pytest.raises(HTTPException) as exc_info:
            await auth_dep(mock_request, mock_credentials)

        assert exc_info.value.status_code == 401
        # Generic exceptions return string error message
        assert "Role authentication failed: Something went wrong" in exc_info.value.detail

    def test_require_role_decorator(self, fastapi_auth):
        """Test require_role decorator creation."""
        # Create decorator
        decorator = fastapi_auth.require_role("admin")

        # Test that it returns a decorator function
        assert callable(decorator)

        # Test decorator on a sample function
        async def test_endpoint():
            return {"message": "success"}

        # Apply decorator
        decorated_endpoint = decorator(test_endpoint)

        # The decorated function should be callable and have the role hint
        assert callable(decorated_endpoint)
        assert hasattr(decorated_endpoint, '__phlow_required_role__')
        assert decorated_endpoint.__phlow_required_role__ == "admin"

    def test_convenience_functions(self):
        """Test convenience functions for creating dependencies."""
        try:
            from phlow.integrations.fastapi import phlow_auth, phlow_auth_role
        except ImportError:
            pytest.skip("FastAPI not installed")

        mock_middleware = MagicMock()

        # Test permission-based auth convenience function
        auth_dep = phlow_auth(mock_middleware, required_permissions=["read:data"])
        assert callable(auth_dep)

        # Test role-based auth convenience function
        role_dep = phlow_auth_role(mock_middleware, "admin")
        assert callable(role_dep)


class TestFastAPIRBACEndToEnd:
    """End-to-end tests for FastAPI RBAC integration."""

    @pytest.fixture
    def app(self):
        """Create FastAPI test app."""
        try:
            from fastapi import Depends, FastAPI

            from phlow.integrations.fastapi import FastAPIPhlowAuth
            from phlow.types import PhlowContext
        except ImportError:
            pytest.skip("FastAPI not installed")

        app = FastAPI()

        # Mock middleware
        mock_middleware = MagicMock()
        auth = FastAPIPhlowAuth(mock_middleware)

        @app.post("/admin")
        async def admin_endpoint(context: PhlowContext = Depends(auth.create_role_auth_dependency("admin"))):
            return {"message": "Admin access granted", "roles": context.verified_roles}

        # Store middleware reference for test access
        app.state.mock_middleware = mock_middleware

        return app

    def test_admin_endpoint_success(self, app):
        """Test successful admin endpoint access."""
        try:
            from fastapi.testclient import TestClient
        except ImportError:
            pytest.skip("FastAPI not installed")

        client = TestClient(app)

        # Mock successful authentication
        mock_context = MagicMock()
        mock_context.verified_roles = ["admin"]
        app.state.mock_middleware.authenticate_with_role = AsyncMock(return_value=mock_context)

        response = client.post(
            "/admin",
            headers={"Authorization": "Bearer test-token"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Admin access granted"
        assert data["roles"] == ["admin"]

    def test_admin_endpoint_unauthorized(self, app):
        """Test unauthorized admin endpoint access."""
        try:
            from fastapi.testclient import TestClient
        except ImportError:
            pytest.skip("FastAPI not installed")

        client = TestClient(app)

        # Mock authentication failure
        app.state.mock_middleware.authenticate_with_role = AsyncMock(
            side_effect=AuthenticationError("Role not verified")
        )

        response = client.post(
            "/admin",
            headers={"Authorization": "Bearer invalid-token"}
        )

        assert response.status_code == 401
        detail = response.json()["detail"]
        assert detail["error"] == "AUTH_ERROR"
        assert detail["message"] == "Role not verified"

    def test_admin_endpoint_no_auth_header(self, app):
        """Test admin endpoint access without auth header."""
        try:
            from fastapi.testclient import TestClient
        except ImportError:
            pytest.skip("FastAPI not installed")

        client = TestClient(app)

        response = client.post("/admin")

        assert response.status_code == 401
        assert "Authorization header required" in response.json()["detail"]
