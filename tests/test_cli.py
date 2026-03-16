"""Tests for phlow CLI."""

import json
import subprocess
import sys

import jwt


def run_cli(*args: str) -> subprocess.CompletedProcess:
    """Run the phlow CLI and return result."""
    return subprocess.run(
        [sys.executable, "-m", "phlow.cli", *args],
        capture_output=True,
        text=True,
    )


class TestGenerateToken:
    def test_generates_token(self):
        result = run_cli("generate-token", "--key", "test-secret", "--agent-id", "a1")
        assert result.returncode == 0
        token = result.stdout.strip()
        claims = jwt.decode(token, "test-secret", algorithms=["HS256"])
        assert claims["sub"] == "a1"

    def test_generates_with_name(self):
        result = run_cli("generate-token", "--key", "secret", "--name", "My Agent")
        assert result.returncode == 0
        token = result.stdout.strip()
        claims = jwt.decode(token, "secret", algorithms=["HS256"])
        assert claims["name"] == "My Agent"

    def test_generates_with_permissions(self):
        result = run_cli(
            "generate-token", "--key", "secret", "--permissions", "read,write"
        )
        assert result.returncode == 0
        token = result.stdout.strip()
        claims = jwt.decode(token, "secret", algorithms=["HS256"])
        assert claims["permissions"] == ["read", "write"]

    def test_requires_key(self):
        result = run_cli("generate-token")
        assert result.returncode != 0


class TestDecodeToken:
    def test_decodes_token(self):
        token = jwt.encode(
            {"sub": "agent-1", "name": "Test"},
            "secret",
            algorithm="HS256",
        )
        result = run_cli("decode-token", token)
        assert result.returncode == 0
        claims = json.loads(result.stdout)
        assert claims["sub"] == "agent-1"

    def test_rejects_garbage(self):
        result = run_cli("decode-token", "garbage")
        assert result.returncode == 1
        assert "Error" in result.stderr


class TestVerifyToken:
    def test_verifies_valid_token(self):
        token = jwt.encode(
            {"sub": "a1", "iat": 1000000000, "exp": 9999999999},
            "secret",
            algorithm="HS256",
        )
        result = run_cli("verify-token", token, "--key", "secret")
        assert result.returncode == 0
        claims = json.loads(result.stdout)
        assert claims["sub"] == "a1"

    def test_rejects_wrong_key(self):
        token = jwt.encode(
            {"sub": "a1", "iat": 1000000000, "exp": 9999999999},
            "correct-key",
            algorithm="HS256",
        )
        result = run_cli("verify-token", token, "--key", "wrong-key")
        assert result.returncode == 1
        assert "failed" in result.stderr.lower()
