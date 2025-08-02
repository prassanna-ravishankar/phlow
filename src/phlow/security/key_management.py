"""
Secure key management module for Phlow.

This module provides interfaces and implementations for secure key storage and retrieval,
replacing the insecure practice of storing keys in environment variables.
"""

import abc
import json
import os
from typing import Any

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

from ..types import PhlowConfig


class KeyStore(abc.ABC):
    """Abstract base class for key storage implementations."""

    @abc.abstractmethod
    def get_private_key(self, key_id: str) -> str | None:
        """Retrieve a private key by ID."""
        pass

    @abc.abstractmethod
    def get_public_key(self, key_id: str) -> str | None:
        """Retrieve a public key by ID."""
        pass

    @abc.abstractmethod
    def store_key_pair(self, key_id: str, private_key: str, public_key: str) -> None:
        """Store a key pair."""
        pass

    @abc.abstractmethod
    def delete_key_pair(self, key_id: str) -> None:
        """Delete a key pair."""
        pass


class EnvironmentKeyStore(KeyStore):
    """
    Legacy environment variable key store for backward compatibility.

    WARNING: This is NOT secure for production use. Use only for development/testing.
    """

    def __init__(self):
        import warnings

        warnings.warn(
            "EnvironmentKeyStore is insecure and should only be used for development. "
            "Use HashiCorpVaultKeyStore or AWSSecretsManagerKeyStore for production.",
            UserWarning,
            stacklevel=2,
        )

    def get_private_key(self, key_id: str) -> str | None:
        return os.environ.get(f"PHLOW_PRIVATE_KEY_{key_id}")

    def get_public_key(self, key_id: str) -> str | None:
        return os.environ.get(f"PHLOW_PUBLIC_KEY_{key_id}")

    def store_key_pair(self, key_id: str, private_key: str, public_key: str) -> None:
        raise NotImplementedError("Environment variables cannot be set at runtime")

    def delete_key_pair(self, key_id: str) -> None:
        raise NotImplementedError("Environment variables cannot be deleted at runtime")


class EncryptedFileKeyStore(KeyStore):
    """
    File-based key store with encryption at rest.

    Stores keys in an encrypted JSON file. Better than environment variables
    but still not ideal for production use.
    """

    def __init__(self, file_path: str, master_key: str | None = None):
        self.file_path = file_path

        if master_key:
            # Ensure master_key is a valid Fernet key (32 bytes, base64-encoded)
            try:
                if isinstance(master_key, str):
                    # Try to use as base64-encoded key first
                    self.cipher = Fernet(master_key.encode())
                else:
                    self.cipher = Fernet(master_key)
            except Exception:
                # If not a valid Fernet key, derive one from the provided string
                import base64
                import hashlib

                key_bytes = hashlib.sha256(
                    master_key.encode() if isinstance(master_key, str) else master_key
                ).digest()
                b64_key = base64.urlsafe_b64encode(key_bytes)
                self.cipher = Fernet(b64_key)
        else:
            # Generate a new master key if not provided
            self.cipher = Fernet(Fernet.generate_key())
            import warnings

            warnings.warn(
                "No master key provided. Generated a random key, but it won't persist across restarts.",
                UserWarning,
                stacklevel=2,
            )

        self._ensure_file_exists()

    def _ensure_file_exists(self):
        """Ensure the key store file exists with secure permissions."""
        if not os.path.exists(self.file_path):
            os.makedirs(os.path.dirname(self.file_path), mode=0o700, exist_ok=True)
            self._save_data({})
            # Set secure file permissions (owner read/write only)
            os.chmod(self.file_path, 0o600)

    def _load_data(self) -> dict[str, Any]:
        """Load and decrypt data from file."""
        if not os.path.exists(self.file_path):
            return {}

        with open(self.file_path, "rb") as f:
            encrypted_data = f.read()
            if not encrypted_data:
                return {}

            decrypted_data = self.cipher.decrypt(encrypted_data)
            return json.loads(decrypted_data.decode())

    def _save_data(self, data: dict[str, Any]):
        """Encrypt and save data to file."""
        json_data = json.dumps(data)
        encrypted_data = self.cipher.encrypt(json_data.encode())

        with open(self.file_path, "wb") as f:
            f.write(encrypted_data)

    def get_private_key(self, key_id: str) -> str | None:
        data = self._load_data()
        key_pair = data.get(key_id, {})
        return key_pair.get("private_key")

    def get_public_key(self, key_id: str) -> str | None:
        data = self._load_data()
        key_pair = data.get(key_id, {})
        return key_pair.get("public_key")

    def store_key_pair(self, key_id: str, private_key: str, public_key: str) -> None:
        data = self._load_data()
        data[key_id] = {"private_key": private_key, "public_key": public_key}
        self._save_data(data)

    def delete_key_pair(self, key_id: str) -> None:
        data = self._load_data()
        if key_id in data:
            del data[key_id]
            self._save_data(data)


class HashiCorpVaultKeyStore(KeyStore):
    """
    HashiCorp Vault key store for production use.

    Provides secure key storage with proper access controls, audit logging,
    and key rotation capabilities.
    """

    def __init__(self, vault_url: str, vault_token: str, mount_point: str = "phlow"):
        try:
            import hvac  # type: ignore
        except ImportError:
            raise ImportError(
                "HashiCorp Vault support requires the 'hvac' package. "
                "Install it with: pip install hvac"
            )

        self.client = hvac.Client(url=vault_url, token=vault_token)
        self.mount_point = mount_point

        if not self.client.is_authenticated():
            raise ValueError("Failed to authenticate with Vault")

    def get_private_key(self, key_id: str) -> str | None:
        try:
            response = self.client.secrets.kv.v2.read_secret_version(
                path=f"keys/{key_id}", mount_point=self.mount_point
            )
            return response["data"]["data"].get("private_key")
        except Exception:
            return None

    def get_public_key(self, key_id: str) -> str | None:
        try:
            response = self.client.secrets.kv.v2.read_secret_version(
                path=f"keys/{key_id}", mount_point=self.mount_point
            )
            return response["data"]["data"].get("public_key")
        except Exception:
            return None

    def store_key_pair(self, key_id: str, private_key: str, public_key: str) -> None:
        self.client.secrets.kv.v2.create_or_update_secret(
            path=f"keys/{key_id}",
            secret={"private_key": private_key, "public_key": public_key},
            mount_point=self.mount_point,
        )

    def delete_key_pair(self, key_id: str) -> None:
        self.client.secrets.kv.v2.delete_metadata_and_all_versions(
            path=f"keys/{key_id}", mount_point=self.mount_point
        )


class AWSSecretsManagerKeyStore(KeyStore):
    """
    AWS Secrets Manager key store for production use on AWS.

    Provides secure key storage with automatic rotation, access controls via IAM,
    and integration with other AWS services.
    """

    def __init__(self, region_name: str | None = None, prefix: str = "phlow/"):
        try:
            import boto3  # type: ignore
        except ImportError:
            raise ImportError(
                "AWS Secrets Manager support requires the 'boto3' package. "
                "Install it with: pip install boto3"
            )

        self.client = boto3.client("secretsmanager", region_name=region_name)
        self.prefix = prefix

    def _secret_name(self, key_id: str) -> str:
        """Generate the full secret name."""
        return f"{self.prefix}{key_id}"

    def get_private_key(self, key_id: str) -> str | None:
        try:
            response = self.client.get_secret_value(SecretId=self._secret_name(key_id))
            secret_data = json.loads(response["SecretString"])
            return secret_data.get("private_key")
        except self.client.exceptions.ResourceNotFoundException:
            return None

    def get_public_key(self, key_id: str) -> str | None:
        try:
            response = self.client.get_secret_value(SecretId=self._secret_name(key_id))
            secret_data = json.loads(response["SecretString"])
            return secret_data.get("public_key")
        except self.client.exceptions.ResourceNotFoundException:
            return None

    def store_key_pair(self, key_id: str, private_key: str, public_key: str) -> None:
        secret_data = json.dumps({"private_key": private_key, "public_key": public_key})

        secret_name = self._secret_name(key_id)

        try:
            # Try to update existing secret
            self.client.update_secret(SecretId=secret_name, SecretString=secret_data)
        except self.client.exceptions.ResourceNotFoundException:
            # Create new secret if it doesn't exist
            self.client.create_secret(
                Name=secret_name,
                SecretString=secret_data,
                Description=f"Phlow key pair for {key_id}",
            )

    def delete_key_pair(self, key_id: str) -> None:
        try:
            self.client.delete_secret(
                SecretId=self._secret_name(key_id), ForceDeleteWithoutRecovery=True
            )
        except self.client.exceptions.ResourceNotFoundException:
            pass  # Already deleted


class KeyManager:
    """
    High-level key management interface.

    Provides key generation, rotation, and retrieval with support for
    multiple storage backends.
    """

    def __init__(self, key_store: KeyStore):
        self.key_store = key_store

    def generate_key_pair(self, key_id: str, key_size: int = 2048) -> tuple[str, str]:
        """Generate a new RSA key pair and store it."""
        private_key = rsa.generate_private_key(public_exponent=65537, key_size=key_size)

        private_pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        ).decode()

        public_pem = (
            private_key.public_key()
            .public_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.SubjectPublicKeyInfo,
            )
            .decode()
        )

        self.key_store.store_key_pair(key_id, private_pem, public_pem)
        return private_pem, public_pem

    def get_key_pair(self, key_id: str) -> tuple[str | None, str | None]:
        """Retrieve a key pair."""
        private_key = self.key_store.get_private_key(key_id)
        public_key = self.key_store.get_public_key(key_id)
        return private_key, public_key

    def rotate_key_pair(self, key_id: str, key_size: int = 2048) -> tuple[str, str]:
        """Rotate a key pair by generating a new one."""
        # Generate new key pair
        new_private, new_public = self.generate_key_pair(f"{key_id}_new", key_size)

        # TODO: Implement proper key rotation with grace period
        # For now, just replace the old key immediately
        self.key_store.store_key_pair(key_id, new_private, new_public)

        return new_private, new_public


def get_key_store(config: PhlowConfig) -> KeyStore:
    """
    Factory function to get the appropriate key store based on configuration.
    """
    key_store_type = os.environ.get("PHLOW_KEY_STORE_TYPE", "environment")

    if key_store_type == "environment":
        return EnvironmentKeyStore()
    elif key_store_type == "encrypted_file":
        file_path = os.environ.get("PHLOW_KEY_STORE_FILE", ".phlow/keys.enc")
        master_key = os.environ.get("PHLOW_MASTER_KEY")
        return EncryptedFileKeyStore(file_path, master_key)
    elif key_store_type == "vault":
        vault_url = os.environ.get("VAULT_URL", "http://localhost:8200")
        vault_token = os.environ.get("VAULT_TOKEN")
        if not vault_token:
            raise ValueError(
                "VAULT_TOKEN environment variable required for Vault key store"
            )
        return HashiCorpVaultKeyStore(vault_url, vault_token)
    elif key_store_type == "aws":
        region = os.environ.get("AWS_REGION")
        return AWSSecretsManagerKeyStore(region_name=region)
    else:
        raise ValueError(f"Unknown key store type: {key_store_type}")
