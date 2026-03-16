"""Tests for security/key_management module."""

import os
import tempfile
import warnings

import pytest

from phlow.security.key_management import (
    EncryptedFileKeyStore,
    EnvironmentKeyStore,
    KeyManager,
    get_key_store,
)
from phlow.types import AgentCard, PhlowConfig


class TestEnvironmentKeyStore:
    def test_warns_on_creation(self):
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            EnvironmentKeyStore()
            assert any("insecure" in str(warning.message).lower() for warning in w)

    def test_get_private_key_from_env(self, monkeypatch):
        monkeypatch.setenv("PHLOW_PRIVATE_KEY_agent1", "my-private-key")
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            store = EnvironmentKeyStore()
        assert store.get_private_key("agent1") == "my-private-key"

    def test_get_public_key_from_env(self, monkeypatch):
        monkeypatch.setenv("PHLOW_PUBLIC_KEY_agent1", "my-public-key")
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            store = EnvironmentKeyStore()
        assert store.get_public_key("agent1") == "my-public-key"

    def test_returns_none_for_missing_key(self):
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            store = EnvironmentKeyStore()
        assert store.get_private_key("nonexistent") is None
        assert store.get_public_key("nonexistent") is None

    def test_store_key_pair_raises(self):
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            store = EnvironmentKeyStore()
        with pytest.raises(NotImplementedError):
            store.store_key_pair("id", "priv", "pub")

    def test_delete_key_pair_raises(self):
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            store = EnvironmentKeyStore()
        with pytest.raises(NotImplementedError):
            store.delete_key_pair("id")


class TestEncryptedFileKeyStore:
    def test_store_and_retrieve_key_pair(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "keys.enc")
            store = EncryptedFileKeyStore(path, master_key="test-master-key-123")

            store.store_key_pair("agent1", "private-key-data", "public-key-data")

            assert store.get_private_key("agent1") == "private-key-data"
            assert store.get_public_key("agent1") == "public-key-data"

    def test_returns_none_for_missing_key(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "keys.enc")
            store = EncryptedFileKeyStore(path, master_key="test-master-key-123")
            assert store.get_private_key("missing") is None
            assert store.get_public_key("missing") is None

    def test_delete_key_pair(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "keys.enc")
            store = EncryptedFileKeyStore(path, master_key="test-master-key-123")

            store.store_key_pair("agent1", "priv", "pub")
            store.delete_key_pair("agent1")

            assert store.get_private_key("agent1") is None

    def test_delete_nonexistent_is_noop(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "keys.enc")
            store = EncryptedFileKeyStore(path, master_key="test-master-key-123")
            store.delete_key_pair("nonexistent")  # Should not raise

    def test_overwrites_existing_key(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "keys.enc")
            store = EncryptedFileKeyStore(path, master_key="test-master-key-123")

            store.store_key_pair("agent1", "old-priv", "old-pub")
            store.store_key_pair("agent1", "new-priv", "new-pub")

            assert store.get_private_key("agent1") == "new-priv"
            assert store.get_public_key("agent1") == "new-pub"

    def test_file_permissions_are_secure(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "keys.enc")
            EncryptedFileKeyStore(path, master_key="test-master-key-123")
            mode = os.stat(path).st_mode & 0o777
            assert mode == 0o600

    def test_warns_without_master_key(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "keys.enc")
            with warnings.catch_warnings(record=True) as w:
                warnings.simplefilter("always")
                EncryptedFileKeyStore(path)
                assert any(
                    "random key" in str(warning.message).lower() for warning in w
                )

    def test_multiple_key_pairs(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "keys.enc")
            store = EncryptedFileKeyStore(path, master_key="test-master-key-123")

            store.store_key_pair("a1", "priv1", "pub1")
            store.store_key_pair("a2", "priv2", "pub2")

            assert store.get_private_key("a1") == "priv1"
            assert store.get_private_key("a2") == "priv2"


class TestKeyManager:
    def test_generate_key_pair(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "keys.enc")
            store = EncryptedFileKeyStore(path, master_key="test-key-123")
            manager = KeyManager(store)

            private_key, public_key = manager.generate_key_pair("test-agent")

            assert "BEGIN" in private_key
            assert "PRIVATE" in private_key
            assert "BEGIN" in public_key
            assert "PUBLIC" in public_key

    def test_get_key_pair(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "keys.enc")
            store = EncryptedFileKeyStore(path, master_key="test-key-123")
            manager = KeyManager(store)

            manager.generate_key_pair("agent-1")
            priv, pub = manager.get_key_pair("agent-1")

            assert priv is not None
            assert pub is not None

    def test_get_missing_key_pair(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "keys.enc")
            store = EncryptedFileKeyStore(path, master_key="test-key-123")
            manager = KeyManager(store)

            priv, pub = manager.get_key_pair("nonexistent")
            assert priv is None
            assert pub is None

    def test_rotate_key_pair(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "keys.enc")
            store = EncryptedFileKeyStore(path, master_key="test-key-123")
            manager = KeyManager(store)

            orig_priv, orig_pub = manager.generate_key_pair("agent-1")
            new_priv, new_pub = manager.rotate_key_pair("agent-1")

            # New keys should be different
            assert new_priv != orig_priv
            assert new_pub != orig_pub

            # Rotated keys should be stored under original ID
            stored_priv, stored_pub = manager.get_key_pair("agent-1")
            assert stored_priv == new_priv
            assert stored_pub == new_pub


class TestGetKeyStore:
    def test_default_returns_environment_store(self, monkeypatch):
        monkeypatch.delenv("PHLOW_KEY_STORE_TYPE", raising=False)
        config = PhlowConfig(
            supabase_url="https://x.supabase.co",
            supabase_anon_key="key",
            agent_card=AgentCard(name="test"),
            private_key="pk",
        )
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            store = get_key_store(config)
        assert isinstance(store, EnvironmentKeyStore)

    def test_encrypted_file_store(self, monkeypatch):
        with tempfile.TemporaryDirectory() as tmpdir:
            monkeypatch.setenv("PHLOW_KEY_STORE_TYPE", "encrypted_file")
            monkeypatch.setenv("PHLOW_KEY_STORE_FILE", os.path.join(tmpdir, "keys.enc"))
            monkeypatch.setenv("PHLOW_MASTER_KEY", "test-master")
            config = PhlowConfig(
                supabase_url="https://x.supabase.co",
                supabase_anon_key="key",
                agent_card=AgentCard(name="test"),
                private_key="pk",
            )
            store = get_key_store(config)
            assert isinstance(store, EncryptedFileKeyStore)

    def test_unknown_store_type_raises(self, monkeypatch):
        monkeypatch.setenv("PHLOW_KEY_STORE_TYPE", "nonexistent")
        config = PhlowConfig(
            supabase_url="https://x.supabase.co",
            supabase_anon_key="key",
            agent_card=AgentCard(name="test"),
            private_key="pk",
        )
        with pytest.raises(ValueError, match="Unknown key store type"):
            get_key_store(config)

    def test_vault_store_requires_token(self, monkeypatch):
        monkeypatch.setenv("PHLOW_KEY_STORE_TYPE", "vault")
        monkeypatch.delenv("VAULT_TOKEN", raising=False)
        config = PhlowConfig(
            supabase_url="https://x.supabase.co",
            supabase_anon_key="key",
            agent_card=AgentCard(name="test"),
            private_key="pk",
        )
        with pytest.raises(ValueError, match="VAULT_TOKEN"):
            get_key_store(config)
