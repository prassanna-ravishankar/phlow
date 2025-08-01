"""Verifiable Credential verification for RBAC."""

import hashlib
import json
import logging
from datetime import datetime, timezone

from supabase import Client

from .types import (
    RoleCredential,
    RoleVerificationResult,
    VerifiablePresentation,
)

logger = logging.getLogger(__name__)


class RoleCredentialVerifier:
    """Verifies role credentials using cryptographic methods."""

    def __init__(self, supabase_client: Client):
        """Initialize verifier with Supabase client.

        Args:
            supabase_client: Supabase client for caching
        """
        self.supabase = supabase_client

    async def verify_presentation(
        self, presentation: VerifiablePresentation, required_role: str
    ) -> RoleVerificationResult:
        """Verify a verifiable presentation contains a valid role credential.

        Args:
            presentation: The verifiable presentation to verify
            required_role: The role that must be present

        Returns:
            Verification result with validity and extracted data
        """
        try:
            # 1. Verify presentation structure
            if not presentation.verifiable_credential:
                return RoleVerificationResult(
                    is_valid=False, error_message="No credentials in presentation"
                )

            # 2. Find role credential in presentation
            role_credential = None
            for cred in presentation.verifiable_credential:
                if "RoleCredential" in cred.type:
                    role_credential = cred
                    break

            if not role_credential:
                return RoleVerificationResult(
                    is_valid=False,
                    error_message="No role credential found in presentation",
                )

            # 3. Verify the role credential
            verification_result = await self._verify_role_credential(
                role_credential, required_role
            )

            if not verification_result.is_valid:
                return verification_result

            # 4. Verify presentation signature (simplified for now)
            presentation_valid = await self._verify_presentation_signature(presentation)

            if not presentation_valid:
                return RoleVerificationResult(
                    is_valid=False, error_message="Invalid presentation signature"
                )

            # 5. Create credential hash for caching
            credential_hash = self._create_credential_hash(role_credential)

            return RoleVerificationResult(
                is_valid=True,
                role=required_role,
                issuer_did=role_credential.issuer,
                expires_at=self._parse_expiration(role_credential.expiration_date),
                credential_hash=credential_hash,
            )

        except Exception as e:
            logger.error(f"Error verifying presentation: {e}")
            return RoleVerificationResult(
                is_valid=False, error_message=f"Verification error: {str(e)}"
            )

    async def _verify_role_credential(
        self, credential: RoleCredential, required_role: str
    ) -> RoleVerificationResult:
        """Verify a single role credential.

        Args:
            credential: The role credential to verify
            required_role: The required role

        Returns:
            Verification result
        """
        # 1. Check credential type
        if "RoleCredential" not in credential.type:
            return RoleVerificationResult(
                is_valid=False, error_message="Not a role credential"
            )

        # 2. Check if credential contains required role
        available_roles = credential.credential_subject.get_roles()
        if required_role not in available_roles:
            return RoleVerificationResult(
                is_valid=False,
                error_message=f"Required role '{required_role}' not found in credential",
            )

        # 3. Check expiration
        if credential.expiration_date:
            expiry = datetime.fromisoformat(
                credential.expiration_date.replace("Z", "+00:00")
            )
            if expiry < datetime.now(timezone.utc):
                return RoleVerificationResult(
                    is_valid=False, error_message="Credential has expired"
                )

        # 4. Verify cryptographic signature (simplified for now)
        signature_valid = await self._verify_credential_signature(credential)

        if not signature_valid:
            return RoleVerificationResult(
                is_valid=False, error_message="Invalid credential signature"
            )

        return RoleVerificationResult(
            is_valid=True,
            role=required_role,
            issuer_did=credential.issuer,
            expires_at=self._parse_expiration(credential.expiration_date),
        )

    async def _verify_credential_signature(self, credential: RoleCredential) -> bool:
        """Verify the cryptographic signature of a credential.

        ⚠️  SECURITY WARNING: This is a simplified mock implementation.
        For production use, implement proper cryptographic verification with:
        1. DID resolution to retrieve issuer's public keys
        2. Signature verification using cryptographic libraries (e.g., PyJWT, cryptography)
        3. Proof purpose and verification method validation
        4. Signature suite support (Ed25519, RSA, ECDSA)

        Args:
            credential: The credential to verify

        Returns:
            True if signature is valid
        """
        # TODO: CRITICAL - Implement actual cryptographic verification for production
        # Current implementation accepts any credential with proof - INSECURE
        
        # Production implementation should:
        # 1. Resolve issuer DID using DID resolution spec
        # 2. Extract public key from DID document
        # 3. Verify signature using appropriate cryptographic method
        # 4. Validate proof purpose matches expected use
        # 5. Check signature suite compatibility
        
        if not credential.proof:
            logger.warning("No proof found in credential")
            return False

        required_fields = ["type", "created", "verification_method", "signature"]
        for field in required_fields:
            if not getattr(credential.proof, field, None):
                logger.warning(f"Missing required proof field: {field}")
                return False

        # WARNING: Mock implementation - accepts any credential with valid proof structure
        logger.warning(
            f"Using mock signature verification for issuer: {credential.issuer} "
            f"(INSECURE - implement proper crypto verification for production)"
        )
        return True

    async def _verify_presentation_signature(
        self, presentation: VerifiablePresentation
    ) -> bool:
        """Verify the cryptographic signature of a presentation.

        ⚠️  SECURITY WARNING: Mock implementation - not cryptographically secure.

        Args:
            presentation: The presentation to verify

        Returns:
            True if signature is valid
        """
        # TODO: CRITICAL - Implement actual cryptographic verification for production
        # Similar to credential verification but for presentations
        if not presentation.proof:
            logger.warning("No proof found in presentation")
            return False

        logger.warning(
            f"Using mock presentation signature verification for holder: {presentation.holder} "
            f"(INSECURE - implement proper crypto verification for production)"
        )
        return True

    def _create_credential_hash(self, credential: RoleCredential) -> str:
        """Create a hash of the credential for caching purposes.

        Args:
            credential: The credential to hash

        Returns:
            SHA-256 hash of the credential
        """
        # Create a stable JSON representation for hashing
        credential_dict = credential.model_dump(by_alias=True, exclude_none=True)
        credential_json = json.dumps(credential_dict, sort_keys=True)
        return hashlib.sha256(credential_json.encode()).hexdigest()

    def _parse_expiration(self, expiration_date: str | None) -> datetime | None:
        """Parse expiration date from credential.

        Args:
            expiration_date: ISO timestamp string

        Returns:
            Parsed datetime or None
        """
        if not expiration_date:
            return None

        try:
            return datetime.fromisoformat(expiration_date.replace("Z", "+00:00"))
        except ValueError:
            logger.warning(f"Invalid expiration date format: {expiration_date}")
            return None
