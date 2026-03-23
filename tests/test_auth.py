"""Tests for PhlowAuth — lightweight JWT auth without Supabase."""

from datetime import datetime, timedelta, timezone

import jwt
import pytest

from phlow.auth import PhlowAuth
from phlow.exceptions import AuthenticationError
from phlow.types import AgentCard

SECRET = "test-secret-key"


class TestPhlowAuthInit:
    def test_creates_with_secret(self):
        auth = PhlowAuth(private_key=SECRET)
        assert auth.algorithm == "HS256"

    def test_detects_rs256_from_pem(self):
        auth = PhlowAuth(private_key="-----BEGIN RSA PRIVATE KEY-----\nfake")
        assert auth.algorithm == "RS256"

    def test_explicit_algorithm(self):
        auth = PhlowAuth(private_key=SECRET, algorithm="HS256")
        assert auth.algorithm == "HS256"

    def test_rejects_empty_key(self):
        with pytest.raises(ValueError, match="private_key is required"):
            PhlowAuth(private_key="")

    def test_rejects_unsupported_algorithm(self):
        with pytest.raises(ValueError, match="Unsupported algorithm"):
            PhlowAuth(private_key=SECRET, algorithm="ES256")

    def test_custom_expiry(self):
        auth = PhlowAuth(private_key=SECRET, token_expiry_hours=24.0)
        assert auth.token_expiry_hours == 24.0


class TestCreateToken:
    def test_creates_minimal_token(self):
        auth = PhlowAuth(private_key=SECRET)
        token = auth.create_token()
        claims = jwt.decode(token, SECRET, algorithms=["HS256"])
        assert "iat" in claims
        assert "exp" in claims

    def test_includes_agent_id_as_sub(self):
        auth = PhlowAuth(private_key=SECRET)
        token = auth.create_token(agent_id="agent-001")
        claims = jwt.decode(token, SECRET, algorithms=["HS256"])
        assert claims["sub"] == "agent-001"

    def test_includes_name(self):
        auth = PhlowAuth(private_key=SECRET)
        token = auth.create_token(name="My Agent")
        claims = jwt.decode(token, SECRET, algorithms=["HS256"])
        assert claims["name"] == "My Agent"

    def test_includes_permissions(self):
        auth = PhlowAuth(private_key=SECRET)
        token = auth.create_token(permissions=["read", "write"])
        claims = jwt.decode(token, SECRET, algorithms=["HS256"])
        assert claims["permissions"] == ["read", "write"]

    def test_includes_extra_claims(self):
        auth = PhlowAuth(private_key=SECRET)
        token = auth.create_token(extra_claims={"team": "infra", "version": 2})
        claims = jwt.decode(token, SECRET, algorithms=["HS256"])
        assert claims["team"] == "infra"
        assert claims["version"] == 2

    def test_custom_expiry(self):
        auth = PhlowAuth(private_key=SECRET)
        token = auth.create_token(expiry_hours=0.5)
        claims = jwt.decode(token, SECRET, algorithms=["HS256"])
        exp = datetime.fromtimestamp(claims["exp"], tz=timezone.utc)
        now = datetime.now(timezone.utc)
        assert (exp - now) < timedelta(minutes=35)

    def test_omits_none_fields(self):
        auth = PhlowAuth(private_key=SECRET)
        token = auth.create_token()
        claims = jwt.decode(token, SECRET, algorithms=["HS256"])
        assert "sub" not in claims
        assert "name" not in claims
        assert "permissions" not in claims


class TestCreateTokenForAgent:
    def test_creates_from_agent_card(self):
        auth = PhlowAuth(private_key=SECRET)
        card = AgentCard(
            name="Test Agent",
            skills=["search"],
            metadata={"agent_id": "a1"},
            permissions=["read"],
        )
        token = auth.create_token_for_agent(card)
        claims = jwt.decode(token, SECRET, algorithms=["HS256"])
        assert claims["sub"] == "a1"
        assert claims["name"] == "Test Agent"
        assert claims["permissions"] == ["read"]
        assert claims["skills"] == ["search"]

    def test_handles_no_metadata(self):
        auth = PhlowAuth(private_key=SECRET)
        card = AgentCard(name="Minimal")
        token = auth.create_token_for_agent(card)
        claims = jwt.decode(token, SECRET, algorithms=["HS256"])
        assert "sub" not in claims
        assert claims["name"] == "Minimal"


class TestVerify:
    def test_verifies_own_token(self):
        auth = PhlowAuth(private_key=SECRET)
        token = auth.create_token(agent_id="a1", name="Agent")
        claims = auth.verify(token)
        assert claims["sub"] == "a1"

    def test_rejects_empty(self):
        auth = PhlowAuth(private_key=SECRET)
        with pytest.raises(AuthenticationError, match="non-empty"):
            auth.verify("")

    def test_rejects_oversized(self):
        auth = PhlowAuth(private_key=SECRET)
        with pytest.raises(AuthenticationError, match="maximum length"):
            auth.verify("x" * 8193)

    def test_rejects_expired(self):
        auth = PhlowAuth(private_key=SECRET)
        token = auth.create_token(expiry_hours=-1)
        with pytest.raises(AuthenticationError, match="expired"):
            auth.verify(token)

    def test_rejects_wrong_key(self):
        auth1 = PhlowAuth(private_key="key-one")
        auth2 = PhlowAuth(private_key="key-two")
        token = auth1.create_token(agent_id="a1")
        with pytest.raises(AuthenticationError, match="signature"):
            auth2.verify(token)

    def test_rejects_garbage(self):
        auth = PhlowAuth(private_key=SECRET)
        with pytest.raises(AuthenticationError, match="Invalid token"):
            auth.verify("not.a.jwt")

    def test_rs256_requires_public_key(self):
        auth = PhlowAuth(private_key="-----BEGIN RSA PRIVATE KEY-----\nfake")
        token = jwt.encode(
            {
                "sub": "x",
                "iat": datetime.now(timezone.utc),
                "exp": datetime.now(timezone.utc) + timedelta(hours=1),
            },
            "dummy",
            algorithm="HS256",
        )
        # Override algorithm to simulate RS256
        auth.algorithm = "RS256"
        with pytest.raises(AuthenticationError, match="Public key required"):
            auth.verify(token)


class TestFastAPIDependency:
    def test_valid_auth(self):
        from fastapi import Depends, FastAPI
        from fastapi.testclient import TestClient

        auth = PhlowAuth(private_key=SECRET)
        dep = auth.create_fastapi_dependency()

        app = FastAPI()

        @app.get("/protected")
        async def protected(claims: dict = Depends(dep)):
            return {"sub": claims.get("sub")}

        client = TestClient(app)
        token = auth.create_token(agent_id="agent-1")
        resp = client.get("/protected", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
        assert resp.json()["sub"] == "agent-1"

    def test_missing_header(self):
        from fastapi import Depends, FastAPI
        from fastapi.testclient import TestClient

        auth = PhlowAuth(private_key=SECRET)
        dep = auth.create_fastapi_dependency()

        app = FastAPI()

        @app.get("/protected")
        async def protected(claims: dict = Depends(dep)):
            return {"ok": True}

        client = TestClient(app)
        resp = client.get("/protected")
        assert resp.status_code == 401

    def test_invalid_token(self):
        from fastapi import Depends, FastAPI
        from fastapi.testclient import TestClient

        auth = PhlowAuth(private_key=SECRET)
        dep = auth.create_fastapi_dependency()

        app = FastAPI()

        @app.get("/protected")
        async def protected(claims: dict = Depends(dep)):
            return {"ok": True}

        client = TestClient(app)
        resp = client.get(
            "/protected", headers={"Authorization": "Bearer bad.token.here"}
        )
        assert resp.status_code == 401

    def test_permission_enforcement(self):
        from fastapi import Depends, FastAPI
        from fastapi.testclient import TestClient

        auth = PhlowAuth(private_key=SECRET)
        dep = auth.create_fastapi_dependency(required_permissions=["admin:write"])

        app = FastAPI()

        @app.get("/admin")
        async def admin(claims: dict = Depends(dep)):
            return {"ok": True}

        client = TestClient(app)

        # Token without permissions — rejected
        token = auth.create_token(agent_id="agent-1")
        resp = client.get("/admin", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 403

        # Token with permissions — accepted
        token = auth.create_token(agent_id="agent-1", permissions=["admin:write"])
        resp = client.get("/admin", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200


class TestRoundTrip:
    """End-to-end: create token, verify it, decode it."""

    def test_full_workflow(self):
        from phlow import decode_token

        auth = PhlowAuth(private_key=SECRET)

        # Create
        token = auth.create_token(
            agent_id="agent-007",
            name="James",
            permissions=["classified:read"],
        )

        # Verify
        claims = auth.verify(token)
        assert claims["sub"] == "agent-007"
        assert claims["permissions"] == ["classified:read"]

        # Decode (no key needed)
        unverified = decode_token(token)
        assert unverified["name"] == "James"
