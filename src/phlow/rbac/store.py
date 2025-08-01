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
        self, role: str, holder_did: str, challenge: str | None = None
    ) -> VerifiablePresentation | None:
        """Create a verifiable presentation for a role.

        Args:
            role: The role to create presentation for
            holder_did: DID of the holder
            challenge: Optional challenge for the presentation

        Returns:
            Verifiable presentation if credential exists
        """
        credential = await self.get_credential(role)
        if not credential:
            return None

        try:
            # Create the presentation
            presentation = VerifiablePresentation(
                verifiableCredential=[credential], holder=holder_did
            )

            # TODO: Add cryptographic proof to presentation
            # For now, create a placeholder proof
            # In production, this would be signed with the holder's private key

            logger.info(
                f"Created presentation for role '{role}' and holder '{holder_did}'"
            )
            return presentation

        except Exception as e:
            logger.error(f"Error creating presentation for role '{role}': {e}")
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
