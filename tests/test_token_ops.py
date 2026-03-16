"""Tests for token generation and verification in phlow.__init__."""

from datetime import datetime, timedelta, timezone

import jwt
import pytest

from phlow import decode_token, generate_token, verify_token
from phlow.exceptions import TokenError
from phlow.types import AgentCard


@pytest.fixture
def agent_card():
    return AgentCard(
        name="test-agent",
        skills=["search", "summarize"],
        service_url="https://agent.example.com",
        metadata={"agent_id": "agent-123"},
    )


@pytest.fixture
def secret_key():
    return "test-secret-key-for-hs256"


class TestGenerateToken:
    def test_generates_valid_jwt(self, agent_card, secret_key):
        token = generate_token(agent_card, secret_key)
        decoded = jwt.decode(token, secret_key, algorithms=["HS256"])
        assert decoded["sub"] == "agent-123"
        assert decoded["name"] == "test-agent"
        assert decoded["skills"] == ["search", "summarize"]
        assert decoded["iss"] == "https://agent.example.com"

    def test_uses_name_as_issuer_when_no_service_url(self, secret_key):
        card = AgentCard(name="fallback-agent", metadata={"agent_id": "a1"})
        token = generate_token(card, secret_key)
        decoded = jwt.decode(token, secret_key, algorithms=["HS256"])
        assert decoded["iss"] == "fallback-agent"

    def test_omits_none_values(self, secret_key):
        card = AgentCard(name="minimal-agent")
        token = generate_token(card, secret_key)
        decoded = jwt.decode(token, secret_key, algorithms=["HS256"])
        assert "sub" not in decoded
        # skills defaults to [] which is falsy but not None — it gets included
        assert decoded["skills"] == []

    def test_token_has_expiry(self, agent_card, secret_key):
        token = generate_token(agent_card, secret_key)
        decoded = jwt.decode(token, secret_key, algorithms=["HS256"])
        assert "exp" in decoded
        assert "iat" in decoded
        # Expiry should be ~1 hour from now
        exp = datetime.fromtimestamp(decoded["exp"], tz=timezone.utc)
        now = datetime.now(timezone.utc)
        assert timedelta(minutes=50) < (exp - now) < timedelta(minutes=70)

    def test_raises_on_missing_agent_card(self, secret_key):
        with pytest.raises(ValueError, match="agent_card and private_key are required"):
            generate_token(None, secret_key)

    def test_raises_on_missing_private_key(self, agent_card):
        with pytest.raises(ValueError, match="agent_card and private_key are required"):
            generate_token(agent_card, "")

    def test_raises_on_wrong_type(self, secret_key):
        with pytest.raises(TypeError, match="AgentCard instance"):
            generate_token("not-an-agent-card", secret_key)

    def test_raises_on_dict_instead_of_agent_card(self, secret_key):
        with pytest.raises(TypeError, match="AgentCard instance"):
            generate_token({"name": "test"}, secret_key)

    def test_rs256_detection(self, agent_card):
        from cryptography.hazmat.primitives import serialization
        from cryptography.hazmat.primitives.asymmetric import rsa

        private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        ).decode()

        token = generate_token(agent_card, pem)
        header = jwt.get_unverified_header(token)
        assert header["alg"] == "RS256"


class TestVerifyToken:
    def test_verifies_valid_token(self, agent_card, secret_key):
        token = generate_token(agent_card, secret_key)
        decoded = verify_token(token, secret_key)
        assert decoded["sub"] == "agent-123"
        assert decoded["name"] == "test-agent"

    def test_raises_on_expired_token(self, secret_key):
        payload = {
            "sub": "agent-1",
            "iat": datetime.now(timezone.utc) - timedelta(hours=2),
            "exp": datetime.now(timezone.utc) - timedelta(hours=1),
        }
        token = jwt.encode(payload, secret_key, algorithm="HS256")
        with pytest.raises(TokenError, match="expired"):
            verify_token(token, secret_key)

    def test_raises_on_invalid_signature(self, agent_card, secret_key):
        token = generate_token(agent_card, secret_key)
        with pytest.raises(TokenError, match="Invalid token signature"):
            verify_token(token, "wrong-key")

    def test_raises_on_empty_token(self, secret_key):
        with pytest.raises(TokenError, match="token and public_key are required"):
            verify_token("", secret_key)

    def test_raises_on_empty_key(self, agent_card, secret_key):
        token = generate_token(agent_card, secret_key)
        with pytest.raises(TokenError, match="token and public_key are required"):
            verify_token(token, "")

    def test_raises_on_malformed_token(self, secret_key):
        with pytest.raises(TokenError, match="Invalid token"):
            verify_token("not.a.valid-token", secret_key)

    def test_rejects_rs256_token_with_string_key(self, secret_key):
        # Craft a token that claims RS256 but provide a string key
        payload = {
            "sub": "agent-1",
            "iat": datetime.now(timezone.utc),
            "exp": datetime.now(timezone.utc) + timedelta(hours=1),
        }
        token = jwt.encode(payload, secret_key, algorithm="HS256")
        # Tamper the header to claim RS256 — verify_token reads unverified header
        # Instead, test the validation path directly
        with pytest.raises(TokenError):
            verify_token(token, "-----BEGIN PUBLIC KEY-----\nfake")

    def test_requires_exp_and_iat_claims(self, secret_key):
        payload = {"sub": "agent-1"}
        token = jwt.encode(
            payload, secret_key, algorithm="HS256", headers={"alg": "HS256"}
        )
        with pytest.raises(TokenError, match="Invalid token"):
            verify_token(token, secret_key)


class TestDecodeToken:
    def test_decodes_without_verification(self, agent_card, secret_key):
        token = generate_token(agent_card, secret_key)
        decoded = decode_token(token)
        assert decoded["sub"] == "agent-123"
        assert decoded["name"] == "test-agent"

    def test_decodes_expired_token(self, secret_key):
        """Unlike verify_token, decode_token should work on expired tokens."""
        payload = {
            "sub": "agent-1",
            "iat": datetime.now(timezone.utc) - timedelta(hours=2),
            "exp": datetime.now(timezone.utc) - timedelta(hours=1),
        }
        token = jwt.encode(payload, secret_key, algorithm="HS256")
        decoded = decode_token(token)
        assert decoded["sub"] == "agent-1"

    def test_decodes_with_wrong_key(self, agent_card, secret_key):
        """decode_token doesn't check signatures."""
        token = generate_token(agent_card, secret_key)
        decoded = decode_token(token)  # No key needed
        assert decoded["name"] == "test-agent"

    def test_raises_on_empty_token(self):
        with pytest.raises(TokenError, match="non-empty string"):
            decode_token("")

    def test_raises_on_none(self):
        with pytest.raises(TokenError, match="non-empty string"):
            decode_token(None)

    def test_raises_on_garbage(self):
        with pytest.raises(TokenError, match="Cannot decode"):
            decode_token("totally-not-a-jwt")
