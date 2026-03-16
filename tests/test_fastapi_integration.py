"""Tests for FastAPI integration module."""

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import jwt
import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from phlow.integrations.fastapi import (
    FastAPIPhlowAuth,
    create_phlow_dependency,
    create_phlow_role_dependency,
    phlow_auth,
    phlow_auth_role,
)
from phlow.middleware import PhlowMiddleware
from phlow.types import AgentCard, PhlowConfig, PhlowContext

SECRET_KEY = "test-fastapi-secret"


def _make_middleware():
    """Create a PhlowMiddleware with mocked externals."""
    config = PhlowConfig(
        supabase_url="https://fake.supabase.co",
        supabase_anon_key="fake-key",
        agent_card=AgentCard(
            name="test-agent",
            description="A test agent for CI",
            service_url="https://test-agent.example.com",
            skills=["search", "summarize"],
            metadata={"agent_id": "agent-001"},
        ),
        private_key=SECRET_KEY,
    )
    with (
        patch("phlow.middleware.create_client") as mock_create,
        patch("phlow.middleware.get_key_store") as mock_ks,
        patch("phlow.middleware.A2AClient"),
    ):
        mock_store = MagicMock()
        mock_store.get_private_key.return_value = None
        mock_store.get_public_key.return_value = None
        mock_ks.return_value = mock_store
        mock_create.return_value = MagicMock()
        return PhlowMiddleware(config)


def _make_token(**overrides):
    payload = {
        "sub": "agent-001",
        "name": "test-agent",
        "iat": datetime.now(timezone.utc),
        "exp": datetime.now(timezone.utc) + timedelta(hours=1),
        **overrides,
    }
    return jwt.encode(payload, SECRET_KEY, algorithm="HS256")


@pytest.fixture
def mw():
    return _make_middleware()


@pytest.fixture
def app(mw):
    app = FastAPI()
    auth = FastAPIPhlowAuth(mw)
    auth_dep = auth.create_auth_dependency()

    @app.get("/protected")
    async def protected(ctx: PhlowContext = Depends(auth_dep)):
        return {"agent": ctx.claims.get("sub")}

    return app


@pytest.fixture
def client(app):
    return TestClient(app)


class TestFastAPIPhlowAuth:
    def test_missing_auth_header(self, client):
        resp = client.get("/protected")
        assert resp.status_code == 401
        assert "Authorization" in resp.json().get("detail", "")

    def test_valid_auth_with_bearer_only(self, client):
        """Auth works with just a Bearer token — no extra headers needed."""
        token = _make_token()
        resp = client.get(
            "/protected",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        assert resp.json()["agent"] == "agent-001"

    def test_invalid_token(self, client):
        resp = client.get(
            "/protected",
            headers={"Authorization": "Bearer invalid.token.here"},
        )
        assert resp.status_code == 401

    def test_expired_token(self, client):
        token = _make_token(
            iat=datetime.now(timezone.utc) - timedelta(hours=2),
            exp=datetime.now(timezone.utc) - timedelta(hours=1),
        )
        resp = client.get(
            "/protected",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 401


class TestPermissionChecking:
    def test_rejects_missing_permission(self, mw):
        app = FastAPI()
        auth = FastAPIPhlowAuth(mw)
        dep = auth.create_auth_dependency(required_permissions=["admin:write"])

        @app.get("/admin")
        async def admin(ctx: PhlowContext = Depends(dep)):
            return {"ok": True}

        client = TestClient(app)
        token = _make_token()
        resp = client.get(
            "/admin",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 403

    def test_allows_permission_from_claims(self, mw):
        """Permissions can come from JWT claims, not just agent metadata."""
        app = FastAPI()
        auth = FastAPIPhlowAuth(mw)
        dep = auth.create_auth_dependency(required_permissions=["read:data"])

        @app.get("/data")
        async def data(ctx: PhlowContext = Depends(dep)):
            return {"ok": True}

        client = TestClient(app)
        token = _make_token(permissions=["read:data", "write:data"])
        resp = client.get(
            "/data",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200


class TestAgentCardRoute:
    def test_serves_agent_card(self, mw):
        app = FastAPI()
        auth = FastAPIPhlowAuth(mw)
        auth.setup_agent_card_route(app)

        client = TestClient(app)
        resp = client.get("/.well-known/agent.json")
        assert resp.status_code == 200

        card = resp.json()
        assert card["name"] == "test-agent"
        assert card["description"] == "A test agent for CI"
        assert card["url"] == "https://test-agent.example.com"
        assert card["id"] == "agent-001"
        assert card["endpoints"]["task"] == "/tasks/send"
        assert card["capabilities"]["search"] is True
        assert card["capabilities"]["summarize"] is True


class TestConvenienceFunctions:
    def test_create_phlow_dependency(self, mw):
        dep = create_phlow_dependency(mw)
        assert callable(dep)

    def test_create_phlow_role_dependency(self, mw):
        dep = create_phlow_role_dependency(mw, "admin")
        assert callable(dep)

    def test_phlow_auth_alias(self, mw):
        dep = phlow_auth(mw)
        assert callable(dep)

    def test_phlow_auth_role_alias(self, mw):
        dep = phlow_auth_role(mw, "admin")
        assert callable(dep)
