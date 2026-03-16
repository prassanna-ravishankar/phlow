"""Tests for PhlowMiddleware core functionality."""

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import jwt
import pytest

from phlow.exceptions import AuthenticationError, ConfigurationError
from phlow.middleware import PhlowMiddleware
from phlow.types import AgentCard, PhlowConfig


@pytest.fixture
def secret_key():
    return "test-middleware-secret-key"


@pytest.fixture
def agent_card():
    return AgentCard(
        name="test-agent",
        description="A test agent",
        service_url="https://agent.test.com",
        skills=["search"],
        metadata={"agent_id": "agent-001"},
    )


@pytest.fixture
def config(agent_card, secret_key):
    return PhlowConfig(
        supabase_url="https://fake.supabase.co",
        supabase_anon_key="fake-anon-key",
        agent_card=agent_card,
        private_key=secret_key,
    )


@pytest.fixture
def middleware(config):
    """Create middleware with mocked external dependencies."""
    with (
        patch("phlow.middleware.create_client") as mock_create,
        patch("phlow.middleware.get_key_store") as mock_key_store,
        patch("phlow.middleware.A2AClient"),
    ):
        mock_store = MagicMock()
        mock_store.get_private_key.return_value = None
        mock_store.get_public_key.return_value = None
        mock_key_store.return_value = mock_store
        mock_create.return_value = MagicMock()

        mw = PhlowMiddleware(config)
        # Reset rate limiter state between tests
        mw.auth_rate_limiter.reset("*")
        yield mw


def _make_token(secret_key, **overrides):
    """Helper to generate a JWT for testing."""
    payload = {
        "sub": "agent-001",
        "name": "test-agent",
        "iat": datetime.now(timezone.utc),
        "exp": datetime.now(timezone.utc) + timedelta(hours=1),
        **overrides,
    }
    return jwt.encode(payload, secret_key, algorithm="HS256")


class TestVerifyToken:
    def test_verifies_valid_token(self, middleware, secret_key):
        token = _make_token(secret_key)
        ctx = middleware.verify_token(token)
        assert ctx.claims["sub"] == "agent-001"
        assert ctx.token == token
        assert ctx.agent.name == "test-agent"

    def test_rejects_empty_token(self, middleware):
        with pytest.raises(AuthenticationError, match="non-empty string"):
            middleware.verify_token("")

    def test_rejects_none_token(self, middleware):
        with pytest.raises(AuthenticationError, match="non-empty string"):
            middleware.verify_token(None)

    def test_rejects_oversized_token(self, middleware):
        with pytest.raises(AuthenticationError, match="maximum length"):
            middleware.verify_token("x" * 8193)

    def test_rejects_malformed_token(self, middleware):
        with pytest.raises(AuthenticationError):
            middleware.verify_token("not-a-jwt")

    def test_rejects_two_segment_token(self, middleware):
        with pytest.raises(AuthenticationError, match="Invalid token format"):
            middleware.verify_token("two.segments")

    def test_rejects_expired_token(self, middleware, secret_key):
        token = _make_token(
            secret_key,
            iat=datetime.now(timezone.utc) - timedelta(hours=2),
            exp=datetime.now(timezone.utc) - timedelta(hours=1),
        )
        with pytest.raises(AuthenticationError, match="expired"):
            middleware.verify_token(token)

    def test_rejects_wrong_signature(self, middleware):
        token = _make_token("wrong-secret-key")
        with pytest.raises(AuthenticationError, match="signature"):
            middleware.verify_token(token)

    def test_rejects_unsupported_algorithm(self, middleware, secret_key):
        # Create token with none algorithm header
        payload = {
            "sub": "agent-001",
            "iat": datetime.now(timezone.utc),
            "exp": datetime.now(timezone.utc) + timedelta(hours=1),
        }
        # Manually craft a token header claiming an unsupported alg
        import base64
        import json

        header = base64.urlsafe_b64encode(
            json.dumps({"alg": "ES256", "typ": "JWT"}).encode()
        ).rstrip(b"=")
        payload_b64 = base64.urlsafe_b64encode(
            json.dumps(payload, default=str).encode()
        ).rstrip(b"=")
        fake_token = f"{header.decode()}.{payload_b64.decode()}.fakesig"

        with pytest.raises(AuthenticationError, match="not in allowed list"):
            middleware.verify_token(fake_token)

    def test_rejects_token_without_key(self, config):
        """Middleware with no private key should reject verification."""
        config_no_key = config.model_copy(update={"private_key": ""})

        with (
            patch("phlow.middleware.create_client") as mock_create,
            patch("phlow.middleware.get_key_store") as mock_key_store,
            patch("phlow.middleware.A2AClient"),
        ):
            mock_store = MagicMock()
            mock_store.get_private_key.return_value = None
            mock_store.get_public_key.return_value = None
            mock_key_store.return_value = mock_store
            mock_create.return_value = MagicMock()

            mw = PhlowMiddleware(config_no_key)

            token = _make_token("any-key")
            with pytest.raises(AuthenticationError, match="No key configured"):
                mw.verify_token(token)


class TestGenerateToken:
    def test_generates_valid_token(self, middleware, secret_key):
        card = AgentCard(name="new-agent", metadata={"agent_id": "new-001"})
        token = middleware.generate_token(card)
        decoded = jwt.decode(token, secret_key, algorithms=["HS256"])
        assert decoded["sub"] == "new-001"
        assert decoded["name"] == "new-agent"

    def test_token_has_expiry(self, middleware, secret_key):
        card = AgentCard(name="agent")
        token = middleware.generate_token(card)
        decoded = jwt.decode(token, secret_key, algorithms=["HS256"])
        assert "exp" in decoded
        assert "iat" in decoded

    def test_no_metadata_omits_sub(self, middleware, secret_key):
        card = AgentCard(name="no-meta")
        token = middleware.generate_token(card)
        decoded = jwt.decode(token, secret_key, algorithms=["HS256"])
        assert "sub" not in decoded


class TestGenerateRlsPolicy:
    def test_generates_valid_policy(self, middleware):
        sql = middleware.generate_rls_policy("agent-1", ["read", "write"])
        assert "agent-1" in sql
        assert "read" in sql
        assert "write" in sql
        assert "CREATE POLICY" in sql

    def test_rejects_sql_injection_in_agent_id(self, middleware):
        with pytest.raises(ValueError, match="alphanumeric"):
            middleware.generate_rls_policy("'; DROP TABLE --", ["read"])

    def test_rejects_sql_injection_in_permissions(self, middleware):
        with pytest.raises(ValueError, match="invalid characters"):
            middleware.generate_rls_policy("agent-1", ["read'; DROP TABLE--"])

    def test_accepts_valid_characters(self, middleware):
        sql = middleware.generate_rls_policy(
            "agent_123-test", ["read:data", "write:logs"]
        )
        assert "agent_123-test" in sql


class TestAuthenticate:
    def test_returns_middleware_function(self, middleware):
        auth_fn = middleware.authenticate()
        assert callable(auth_fn)

    def test_rejects_missing_auth_header(self, middleware):
        auth_fn = middleware.authenticate()
        request = MagicMock()
        request.headers = {}

        with pytest.raises(AuthenticationError, match="Missing or invalid"):
            auth_fn(request)

    def test_rejects_non_bearer_header(self, middleware):
        auth_fn = middleware.authenticate()
        request = MagicMock()
        request.headers = {"authorization": "Basic abc123"}

        with pytest.raises(AuthenticationError, match="Missing or invalid"):
            auth_fn(request)

    def test_attaches_context_to_request(self, middleware, secret_key):
        auth_fn = middleware.authenticate()
        token = _make_token(secret_key)
        request = MagicMock()
        request.headers = {"authorization": f"Bearer {token}"}

        result = auth_fn(request)
        assert result.phlow.claims["sub"] == "agent-001"


class TestGenerateNonce:
    def test_returns_16_char_alphanumeric(self, middleware):
        nonce = middleware._generate_nonce()
        assert len(nonce) == 16
        assert nonce.isalnum()

    def test_unique_nonces(self, middleware):
        nonces = {middleware._generate_nonce() for _ in range(100)}
        assert len(nonces) == 100


class TestAccessors:
    def test_get_a2a_client(self, middleware):
        assert middleware.get_a2a_client() is not None

    def test_get_supabase_client(self, middleware):
        assert middleware.get_supabase_client() is not None


class TestAsyncContextManager:
    @pytest.mark.asyncio
    async def test_aclose(self, middleware):
        await middleware.aclose()

    @pytest.mark.asyncio
    async def test_context_manager(self, config):
        with (
            patch("phlow.middleware.create_client") as mock_create,
            patch("phlow.middleware.get_key_store") as mock_key_store,
            patch("phlow.middleware.A2AClient"),
        ):
            mock_store = MagicMock()
            mock_store.get_private_key.return_value = None
            mock_store.get_public_key.return_value = None
            mock_key_store.return_value = mock_store
            mock_create.return_value = MagicMock()

            async with PhlowMiddleware(config) as mw:
                assert mw is not None


class TestConfigValidation:
    def test_rejects_empty_supabase_url(self, agent_card, secret_key):
        config = PhlowConfig(
            supabase_url="",
            supabase_anon_key="key",
            agent_card=agent_card,
            private_key=secret_key,
        )
        with (
            patch("phlow.middleware.create_client"),
            patch("phlow.middleware.get_key_store") as mock_ks,
            patch("phlow.middleware.A2AClient"),
        ):
            mock_store = MagicMock()
            mock_store.get_private_key.return_value = None
            mock_store.get_public_key.return_value = None
            mock_ks.return_value = mock_store

            with pytest.raises(ConfigurationError, match="required"):
                PhlowMiddleware(config)
