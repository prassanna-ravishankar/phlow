"""Tests for RBAC middleware functionality."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from phlow.exceptions import AuthenticationError
from phlow.middleware import PhlowMiddleware
from phlow.rbac.types import (
    CachedRole,
    RoleVerificationResult,
    VerifiablePresentation,
)
from phlow.types import AgentCard, PhlowConfig


class TestPhlowMiddlewareRBAC:
    """Test RBAC functionality in PhlowMiddleware."""

    @pytest.fixture
    def mock_config(self):
        """Create mock Phlow configuration."""
        config = MagicMock(spec=PhlowConfig)
        config.supabase_url = "https://test.supabase.co"
        config.supabase_anon_key = "test-anon-key"
        config.private_key = "test-private-key"
        config.agent_card = MagicMock(spec=AgentCard)
        config.agent_card.name = "Test Agent"
        config.agent_card.description = "Test agent for RBAC"
        config.agent_card.service_url = "https://test-agent.com"
        config.agent_card.skills = []
        config.agent_card.security_schemes = {}
        config.agent_card.metadata = {"agent_id": "test-agent-123"}
        return config

    @pytest.fixture
    def middleware(self, mock_config):
        """Create PhlowMiddleware instance with mocked dependencies."""
        with (
            patch("phlow.middleware.create_client"),
            patch("phlow.middleware.httpx.AsyncClient"),
            patch("phlow.middleware.A2AClient"),
            patch.object(PhlowMiddleware, "_convert_to_a2a_agent_card") as mock_convert,
        ):
            # Mock the A2A conversion to avoid validation errors
            mock_convert.return_value = MagicMock()

            middleware = PhlowMiddleware(mock_config)

            # Mock the RBAC components
            middleware.role_verifier = MagicMock()
            middleware.role_cache = MagicMock()

            return middleware

    @pytest.fixture
    def valid_token(self):
        """Create a valid JWT token for testing."""
        return "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJ0ZXN0LWFnZW50LTEyMyIsIm5hbWUiOiJUZXN0IEFnZW50IiwiaWF0IjoxNjQwOTk1MjAwLCJleHAiOjE2NDA5OTg4MDB9.test-signature"

    @pytest.mark.asyncio
    async def test_authenticate_with_role_cached_valid(self, middleware, valid_token):
        """Test role authentication with valid cached role."""
        # Mock cached role that's not expired
        cached_role = CachedRole(
            agent_id="test-agent-123",
            role="admin",
            verified_at=datetime.now(timezone.utc),
            credential_hash="test-hash",
        )

        middleware.role_cache.get_cached_role = AsyncMock(return_value=cached_role)
        middleware.role_cache.is_expired = MagicMock(return_value=False)

        # Mock verify_token to return valid context
        with patch.object(middleware, "verify_token") as mock_verify:
            mock_context = MagicMock()
            mock_context.agent.metadata = {"agent_id": "test-agent-123"}
            mock_verify.return_value = mock_context

            context = await middleware.authenticate_with_role(valid_token, "admin")

            assert context.verified_roles == ["admin"]
            middleware.role_cache.get_cached_role.assert_called_once_with(
                "test-agent-123", "admin"
            )

    @pytest.mark.asyncio
    async def test_authenticate_with_role_no_agent_id(self, middleware, valid_token):
        """Test role authentication with missing agent ID."""
        with patch.object(middleware, "verify_token") as mock_verify:
            mock_context = MagicMock()
            mock_context.agent.metadata = {}  # No agent_id
            mock_verify.return_value = mock_context

            with pytest.raises(AuthenticationError, match="Agent ID not found"):
                await middleware.authenticate_with_role(valid_token, "admin")

    @pytest.mark.asyncio
    async def test_authenticate_with_role_cache_expired(self, middleware, valid_token):
        """Test role authentication with expired cache."""
        # Mock expired cached role
        cached_role = CachedRole(
            agent_id="test-agent-123",
            role="admin",
            verified_at=datetime.now(timezone.utc),
            expires_at=datetime(2020, 1, 1, tzinfo=timezone.utc),  # Expired
            credential_hash="test-hash",
        )

        middleware.role_cache.get_cached_role = AsyncMock(return_value=cached_role)
        middleware.role_cache.is_expired = MagicMock(return_value=True)

        # Mock successful credential request
        mock_response = {
            "type": "role-credential-response",
            "nonce": "test-nonce",
            "error": "Role 'admin' not available",
        }

        with (
            patch.object(middleware, "verify_token") as mock_verify,
            patch.object(
                middleware, "_send_role_credential_request", return_value=mock_response
            ),
        ):
            mock_context = MagicMock()
            mock_context.agent.metadata = {"agent_id": "test-agent-123"}
            mock_verify.return_value = mock_context

            with pytest.raises(
                AuthenticationError, match="Role credential request failed"
            ):
                await middleware.authenticate_with_role(valid_token, "admin")

    @pytest.mark.asyncio
    async def test_authenticate_with_role_successful_verification(
        self, middleware, valid_token
    ):
        """Test successful role authentication with credential verification."""
        # No cached role
        middleware.role_cache.get_cached_role = AsyncMock(return_value=None)

        # Mock successful verification
        verification_result = RoleVerificationResult(
            is_valid=True,
            role="admin",
            issuer_did="did:example:issuer",
            credential_hash="test-hash",
        )
        middleware.role_verifier.verify_presentation = AsyncMock(
            return_value=verification_result
        )
        middleware.role_cache.cache_verified_role = AsyncMock(return_value=True)

        # Mock successful credential request with presentation
        mock_presentation = MagicMock(spec=VerifiablePresentation)
        mock_response = {
            "type": "role-credential-response",
            "nonce": "test-nonce",
            "presentation": mock_presentation,
        }

        with (
            patch.object(middleware, "verify_token") as mock_verify,
            patch.object(
                middleware, "_send_role_credential_request", return_value=mock_response
            ),
            patch("phlow.middleware.RoleCredentialResponse") as mock_response_class,
        ):
            mock_context = MagicMock()
            mock_context.agent.metadata = {"agent_id": "test-agent-123"}
            mock_verify.return_value = mock_context

            # Mock the RoleCredentialResponse creation
            mock_response_obj = MagicMock()
            mock_response_obj.presentation = mock_presentation
            mock_response_obj.error = None
            mock_response_class.return_value = mock_response_obj

            context = await middleware.authenticate_with_role(valid_token, "admin")

            assert context.verified_roles == ["admin"]
            middleware.role_verifier.verify_presentation.assert_called_once()
            middleware.role_cache.cache_verified_role.assert_called_once()

    @pytest.mark.asyncio
    async def test_authenticate_with_role_verification_failed(
        self, middleware, valid_token
    ):
        """Test role authentication with failed verification."""
        # No cached role
        middleware.role_cache.get_cached_role = AsyncMock(return_value=None)

        # Mock failed verification
        verification_result = RoleVerificationResult(
            is_valid=False, error_message="Invalid signature"
        )
        middleware.role_verifier.verify_presentation = AsyncMock(
            return_value=verification_result
        )

        # Mock credential request with presentation
        mock_presentation = MagicMock(spec=VerifiablePresentation)
        mock_response = {
            "type": "role-credential-response",
            "nonce": "test-nonce",
            "presentation": mock_presentation,
        }

        with (
            patch.object(middleware, "verify_token") as mock_verify,
            patch.object(
                middleware, "_send_role_credential_request", return_value=mock_response
            ),
            patch("phlow.middleware.RoleCredentialResponse") as mock_response_class,
        ):
            mock_context = MagicMock()
            mock_context.agent.metadata = {"agent_id": "test-agent-123"}
            mock_verify.return_value = mock_context

            # Mock the RoleCredentialResponse creation
            mock_response_obj = MagicMock()
            mock_response_obj.presentation = mock_presentation
            mock_response_obj.error = None
            mock_response_class.return_value = mock_response_obj

            with pytest.raises(
                AuthenticationError, match="Role credential verification failed"
            ):
                await middleware.authenticate_with_role(valid_token, "admin")

    @pytest.mark.asyncio
    async def test_authenticate_with_role_no_response(self, middleware, valid_token):
        """Test role authentication with no credential response."""
        # No cached role
        middleware.role_cache.get_cached_role = AsyncMock(return_value=None)

        with (
            patch.object(middleware, "verify_token") as mock_verify,
            patch.object(
                middleware, "_send_role_credential_request", return_value=None
            ),
        ):
            mock_context = MagicMock()
            mock_context.agent.metadata = {"agent_id": "test-agent-123"}
            mock_verify.return_value = mock_context

            with pytest.raises(AuthenticationError, match="No response received"):
                await middleware.authenticate_with_role(valid_token, "admin")

    def test_generate_nonce(self, middleware):
        """Test nonce generation."""
        nonce1 = middleware._generate_nonce()
        nonce2 = middleware._generate_nonce()

        assert len(nonce1) == 16
        assert len(nonce2) == 16
        assert nonce1 != nonce2  # Should be different
        assert nonce1.isalnum()  # Should be alphanumeric

    @pytest.mark.asyncio
    async def test_send_role_credential_request(self, middleware):
        """Test sending role credential request with mocked HTTP response."""
        from unittest.mock import AsyncMock, MagicMock, patch

        from phlow.rbac.types import RoleCredentialRequest

        request = RoleCredentialRequest(required_role="admin", nonce="test-nonce")

        # Mock the agent endpoint resolution to return a valid URL
        with patch.object(middleware, "_resolve_agent_endpoint") as mock_resolve:
            mock_resolve.return_value = "https://test-agent.example.com"

            # Mock the HTTP response
            mock_response = MagicMock()
            mock_response.json.return_value = {
                "status": "completed",
                "result": {
                    "type": "role-credential-response",
                    "nonce": "test-nonce",
                    "error": "Role 'admin' not available for testing",
                },
            }
            mock_response.raise_for_status.return_value = None

            # Mock the httpx.AsyncClient properly
            async def mock_post(*args, **kwargs):
                return mock_response

            mock_client = MagicMock()
            mock_client.post = mock_post

            with patch("httpx.AsyncClient") as mock_client_class:
                # Set up the async context manager
                mock_client_class.return_value.__aenter__ = AsyncMock(
                    return_value=mock_client
                )
                mock_client_class.return_value.__aexit__ = AsyncMock(return_value=None)

                response = await middleware._send_role_credential_request(
                    "test-agent", request
                )

        assert response is not None
        assert response["type"] == "role-credential-response"
        assert response["nonce"] == "test-nonce"
        assert "error" in response  # Test expects error response
        mock_resolve.assert_called_once_with("test-agent")
