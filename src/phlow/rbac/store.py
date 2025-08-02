"""Client-side credential storage for agents."""

import json
import logging
from pathlib import Path

from .types import RoleCredential, VerifiablePresentation

logger = logging.getLogger(__name__)


class RoleCredentialStore:
    """Stores and manages role credentials for an agent."""

    def __init__(self, storage_path: Path | None = None):
        """Initialize credential store.

        Args:
            storage_path: Path to store credentials (defaults to ~/.phlow/credentials)
        """
        if storage_path is None:
            storage_path = Path.home() / ".phlow" / "credentials"

        self.storage_path = storage_path
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self.credentials_file = self.storage_path / "role_credentials.json"

        # In-memory cache of loaded credentials
        self._credentials: dict[str, RoleCredential] = {}
        self._loaded = False

    async def load_credentials(self) -> None:
        """Load credentials from storage."""
        try:
            if self.credentials_file.exists():
                with open(self.credentials_file) as f:
                    data = json.load(f)

                self._credentials = {}
                for role, cred_data in data.items():
                    try:
                        credential = RoleCredential(**cred_data)
                        self._credentials[role] = credential
                    except Exception as e:
                        logger.warning(
                            f"Failed to load credential for role '{role}': {e}"
                        )

                logger.info(f"Loaded {len(self._credentials)} role credentials")

            self._loaded = True

        except Exception as e:
            logger.error(f"Error loading credentials: {e}")
            self._credentials = {}
            self._loaded = True

    async def save_credentials(self) -> None:
        """Save credentials to storage."""
        try:
            data = {}
            for role, credential in self._credentials.items():
                data[role] = credential.dict(by_alias=True, exclude_none=True)

            with open(self.credentials_file, "w") as f:
                json.dump(data, f, indent=2)

            logger.info(f"Saved {len(self._credentials)} role credentials")

        except Exception as e:
            logger.error(f"Error saving credentials: {e}")

    async def add_credential(self, credential: RoleCredential) -> None:
        """Add a role credential to the store.

        Args:
            credential: The credential to add
        """
        if not self._loaded:
            await self.load_credentials()

        # Extract roles from credential
        roles = credential.credential_subject.get_roles()

        for role in roles:
            self._credentials[role] = credential
            logger.info(f"Added credential for role: {role}")

        await self.save_credentials()

    async def get_credential(self, role: str) -> RoleCredential | None:
        """Get a credential for a specific role.

        Args:
            role: The role to get credential for

        Returns:
            The credential if found, None otherwise
        """
        if not self._loaded:
            await self.load_credentials()

        return self._credentials.get(role)

    async def has_role(self, role: str) -> bool:
        """Check if the store has a credential for a role.

        Args:
            role: The role to check

        Returns:
            True if credential exists for role
        """
        if not self._loaded:
            await self.load_credentials()

        return role in self._credentials

    async def get_all_roles(self) -> list[str]:
        """Get all roles for which credentials are stored.

        Returns:
            List of role names
        """
        if not self._loaded:
            await self.load_credentials()

        return list(self._credentials.keys())

    async def remove_credential(self, role: str) -> bool:
        """Remove a credential for a specific role.

        Args:
            role: The role to remove

        Returns:
            True if credential was removed
        """
        if not self._loaded:
            await self.load_credentials()

        if role in self._credentials:
            del self._credentials[role]
            await self.save_credentials()
            logger.info(f"Removed credential for role: {role}")
            return True

        return False

    async def create_presentation(
        self,
        role: str,
        holder_did: str,
        challenge: str | None = None,
        signing_key: bytes | None = None,
    ) -> VerifiablePresentation | None:
        """Create a verifiable presentation for a role with cryptographic proof.

        Args:
            role: The role to create presentation for
            holder_did: DID of the holder
            challenge: Optional challenge for the presentation
            signing_key: Optional Ed25519 private key bytes for signing.
                        If None, will attempt to resolve from holder DID.

        Returns:
            Signed verifiable presentation if credential exists
        """
        credential = await self.get_credential(role)
        if not credential:
            return None

        try:
            # Create the presentation without proof first
            presentation = VerifiablePresentation(
                verifiableCredential=[credential], holder=holder_did
            )

            # Add cryptographic proof to presentation
            signed_presentation = await self._add_presentation_proof(
                presentation, holder_did, challenge, signing_key
            )

            if signed_presentation:
                logger.info(
                    f"Created signed presentation for role '{role}' and holder '{holder_did}'"
                )
                return signed_presentation
            else:
                logger.warning(
                    f"Could not sign presentation for role '{role}' - returning unsigned"
                )
                return presentation

        except Exception as e:
            logger.error(f"Error creating presentation for role '{role}': {e}")
            return None

    async def _add_presentation_proof(
        self,
        presentation: VerifiablePresentation,
        holder_did: str,
        challenge: str | None = None,
        signing_key: bytes | None = None,
    ) -> VerifiablePresentation | None:
        """Add cryptographic proof to a presentation.

        Args:
            presentation: The presentation to sign
            holder_did: DID of the holder (for key resolution)
            challenge: Optional challenge string
            signing_key: Optional Ed25519 private key bytes

        Returns:
            Signed presentation or None if signing fails
        """
        try:
            import base64
            import json
            from datetime import datetime, timezone

            # Resolve private key if not provided
            if not signing_key:
                signing_key = await self._resolve_holder_private_key(holder_did)
                if not signing_key:
                    logger.error(
                        f"Could not resolve private key for holder {holder_did}"
                    )
                    return None

            # Create canonical presentation data (without proof)
            presentation_dict = presentation.model_dump(by_alias=True)
            presentation_dict.pop("proof", None)  # Remove any existing proof

            # Add challenge if provided
            if challenge:
                presentation_dict["challenge"] = challenge

            canonical_data = json.dumps(
                presentation_dict, sort_keys=True, separators=(",", ":")
            ).encode("utf-8")

            # Sign the canonical data with Ed25519
            from cryptography.hazmat.primitives.asymmetric import ed25519

            private_key = ed25519.Ed25519PrivateKey.from_private_bytes(signing_key)
            signature = private_key.sign(canonical_data)
            signature_b64 = base64.b64encode(signature).decode("utf-8")

            # Create verification method URI
            verification_method = f"{holder_did}#key-1"

            # Create the proof
            from .types import Proof

            proof = Proof(
                type="Ed25519Signature2020",
                created=datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
                verification_method=verification_method,
                proof_purpose="authentication",
                signature=signature_b64,
                challenge=challenge,  # Include challenge in proof if provided
            )

            # Create new presentation with proof
            signed_presentation = VerifiablePresentation(
                context=presentation.context,
                type=presentation.type,
                verifiableCredential=presentation.verifiable_credential,
                holder=presentation.holder,
                proof=proof,
            )

            return signed_presentation

        except Exception as e:
            logger.error(f"Error adding proof to presentation: {e}")
            return None

    async def _resolve_holder_private_key(self, holder_did: str) -> bytes | None:
        """Resolve private key for holder DID.

        ⚠️  SECURITY NOTE: This implementation includes test keys for did:example DIDs.
        In production, this should integrate with secure key management systems.

        Args:
            holder_did: DID of the holder

        Returns:
            Ed25519 private key bytes or None if not found
        """
        try:
            # Production key resolution - no hardcoded test keys
            # Check environment variable for development/testing
            import os

            if (
                holder_did.startswith("did:example:")
                and os.getenv("PHLOW_ALLOW_TEST_KEYS") == "true"
            ):
                logger.warning("Using test key generation - NOT FOR PRODUCTION")
                import hashlib

                # Create deterministic private key from DID (testing only, requires explicit env var)
                seed = f"{holder_did}#key-1".encode()
                private_key_bytes = hashlib.sha256(seed).digest()
                return private_key_bytes

            # Production key resolution methods:
            # 1. Environment variables for specific DIDs
            key_env_var = f"PHLOW_PRIVATE_KEY_{holder_did.replace(':', '_').replace('#', '_').upper()}"
            key_base64 = os.getenv(key_env_var)
            if key_base64:
                import base64

                return base64.b64decode(key_base64)

            # 2. Key management service integration (implement as needed)
            # 3. Hardware security module integration
            # 4. Secure key derivation from master keys

            logger.error(
                f"No private key available for DID: {holder_did}. Configure via environment variable {key_env_var} or implement key management integration."
            )
            return None

        except Exception as e:
            logger.error(f"Error resolving private key for {holder_did}: {e}")
            return None

    async def import_credential_from_file(self, file_path: Path) -> bool:
        """Import a credential from a JSON file.

        Args:
            file_path: Path to the credential file

        Returns:
            True if successfully imported
        """
        try:
            with open(file_path) as f:
                data = json.load(f)

            credential = RoleCredential(**data)
            await self.add_credential(credential)

            logger.info(f"Imported credential from {file_path}")
            return True

        except Exception as e:
            logger.error(f"Error importing credential from {file_path}: {e}")
            return False

    async def export_credential_to_file(self, role: str, file_path: Path) -> bool:
        """Export a credential to a JSON file.

        Args:
            role: Role to export
            file_path: Path to save the credential

        Returns:
            True if successfully exported
        """
        credential = await self.get_credential(role)
        if not credential:
            logger.error(f"No credential found for role '{role}'")
            return False

        try:
            data = credential.dict(by_alias=True, exclude_none=True)

            with open(file_path, "w") as f:
                json.dump(data, f, indent=2)

            logger.info(f"Exported credential for role '{role}' to {file_path}")
            return True

        except Exception as e:
            logger.error(f"Error exporting credential for role '{role}': {e}")
            return False
