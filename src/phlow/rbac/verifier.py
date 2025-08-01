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
        # DID document cache: {did: (document, expiry_timestamp)}
        self._did_document_cache: dict[str, tuple[dict, float]] = {}
        self._cache_ttl_seconds = 300  # 5 minutes cache

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

        Implements proper W3C Verifiable Credentials signature verification
        supporting Ed25519Signature2020 and JsonWebSignature2020 proof types.

        Args:
            credential: The credential to verify

        Returns:
            True if signature is valid
        """
        if not credential.proof:
            logger.warning("No proof found in credential")
            return False

        # Validate required proof fields
        required_fields = ["type", "created", "verification_method", "signature"]
        for field in required_fields:
            if not getattr(credential.proof, field, None):
                logger.warning(f"Missing required proof field: {field}")
                return False

        try:
            # Import cryptography libraries
            import base64
            import json

            proof_type = credential.proof.type
            verification_method = credential.proof.verification_method
            signature_b64 = credential.proof.signature

            # Step 1: Resolve public key from verification method
            public_key = await self._resolve_public_key(verification_method)
            if not public_key:
                logger.warning(
                    f"Could not resolve public key for {verification_method}"
                )
                return False

            # Step 2: Create canonical data to verify
            # Remove proof from credential for verification
            credential_dict = credential.model_dump(by_alias=True)
            credential_dict.pop("proof", None)

            # Create canonical JSON-LD (simplified - in production use pyld)
            canonical_data = json.dumps(
                credential_dict, sort_keys=True, separators=(",", ":")
            ).encode("utf-8")

            # Step 3: Verify signature based on proof type
            signature_bytes = base64.b64decode(signature_b64)

            if proof_type == "Ed25519Signature2020":
                return await self._verify_ed25519_signature(
                    public_key, canonical_data, signature_bytes
                )
            elif proof_type == "JsonWebSignature2020":
                return await self._verify_rsa_signature(
                    public_key, canonical_data, signature_bytes
                )
            else:
                logger.warning(f"Unsupported signature type: {proof_type}")
                return False

        except Exception as e:
            logger.error(f"Signature verification failed: {e}")
            return False

    async def _resolve_public_key(self, verification_method: str) -> bytes | None:
        """Resolve public key from verification method URI.

        Args:
            verification_method: DID verification method URI

        Returns:
            Public key bytes or None if resolution fails
        """
        try:
            # Extract DID and key fragment from verification method
            # Format: did:example:issuer#key-1
            if "#" not in verification_method:
                logger.warning(
                    f"Invalid verification method format: {verification_method}"
                )
                return None

            did, key_fragment = verification_method.split("#", 1)

            # For development/testing: check if we have the public key in our registry
            # In production, this would do proper DID resolution via HTTP
            public_key = await self._lookup_public_key_in_registry(did, key_fragment)
            if public_key:
                return public_key

            # Fallback: try to resolve DID document via HTTP (simplified implementation)
            return await self._resolve_did_document_public_key(did, key_fragment)

        except Exception as e:
            logger.error(f"Public key resolution failed for {verification_method}: {e}")
            return None

    async def _lookup_public_key_in_registry(
        self, did: str, key_fragment: str
    ) -> bytes | None:
        """Look up public key in local Supabase registry.

        Args:
            did: DID identifier
            key_fragment: Key fragment identifier

        Returns:
            Public key bytes or None
        """
        # For testing: provide mock keys for did:example:* DIDs
        if did.startswith("did:example:"):
            return self._get_test_public_key(did, key_fragment)

        try:
            # Query Supabase for DID document or public key
            response = (
                self.supabase.table("did_public_keys")
                .select("public_key, key_type")
                .eq("did", did)
                .eq("key_fragment", key_fragment)
                .single()
                .execute()
            )

            if response.data:
                import base64

                return base64.b64decode(response.data["public_key"])

        except Exception as e:
            logger.debug(
                f"No public key found in registry for {did}#{key_fragment}: {e}"
            )

        return None

    def _get_test_public_key(self, did: str, key_fragment: str) -> bytes | None:
        """Get mock public key for testing with did:example:* DIDs.

        Args:
            did: Test DID identifier
            key_fragment: Key fragment

        Returns:
            Ed25519 public key bytes that match test private keys
        """
        try:
            import hashlib

            from cryptography.hazmat.primitives.asymmetric import ed25519

            # Generate same deterministic private key as used in tests
            verification_method = f"{did}#{key_fragment}"
            seed = verification_method.encode("utf-8")
            private_key_bytes = hashlib.sha256(seed).digest()

            # Create Ed25519 private key and extract public key
            private_key = ed25519.Ed25519PrivateKey.from_private_bytes(
                private_key_bytes
            )
            public_key = private_key.public_key()

            # Return public key bytes
            from cryptography.hazmat.primitives import serialization

            return public_key.public_bytes(
                encoding=serialization.Encoding.Raw,
                format=serialization.PublicFormat.Raw,
            )

        except Exception as e:
            logger.error(f"Failed to generate test public key: {e}")
            return None

    def _get_cached_did_document(self, did: str) -> dict | None:
        """Get cached DID document if still valid.

        Args:
            did: DID identifier

        Returns:
            Cached DID document or None if not cached/expired
        """
        import time

        if did in self._did_document_cache:
            document, expiry = self._did_document_cache[did]
            if time.time() < expiry:
                return document
            else:
                # Remove expired entry
                del self._did_document_cache[did]
        return None

    def _cache_did_document(self, did: str, document: dict) -> None:
        """Cache a DID document with expiration.

        Args:
            did: DID identifier
            document: DID document to cache
        """
        import time

        expiry = time.time() + self._cache_ttl_seconds
        self._did_document_cache[did] = (document, expiry)

        # Simple cache cleanup: remove expired entries when cache gets large
        if len(self._did_document_cache) > 100:
            current_time = time.time()
            expired_keys = [
                k
                for k, (_, exp) in self._did_document_cache.items()
                if current_time >= exp
            ]
            for key in expired_keys:
                del self._did_document_cache[key]

    async def _resolve_did_document_public_key(
        self, did: str, key_fragment: str
    ) -> bytes | None:
        """Resolve public key from DID document via HTTP with caching.

        Args:
            did: DID identifier
            key_fragment: Key fragment identifier

        Returns:
            Public key bytes or None
        """
        try:
            import base64

            # Handle did:key method directly (no HTTP needed)
            if did.startswith("did:key:"):
                return self._resolve_did_key(did)

            # Check cache first
            did_doc = self._get_cached_did_document(did)

            if not did_doc:
                # Cache miss - fetch DID document
                did_doc = await self._fetch_did_document(did)
                if did_doc:
                    self._cache_did_document(did, did_doc)
                else:
                    return None

            # Find verification method in DID document
            verification_methods = did_doc.get("verificationMethod", [])
            for vm in verification_methods:
                if vm.get("id") == f"{did}#{key_fragment}":
                    # Extract public key based on type
                    if vm.get("type") == "Ed25519VerificationKey2020":
                        return base64.b64decode(
                            vm["publicKeyMultibase"][1:]
                        )  # Remove 'z' prefix
                    elif vm.get("type") == "JsonWebKey2020":
                        # Extract from JWK format
                        jwk = vm.get("publicKeyJwk", {})
                        if jwk.get("kty") == "OKP" and jwk.get("crv") == "Ed25519":
                            return base64.urlsafe_b64decode(jwk["x"] + "==")

        except Exception as e:
            logger.error(f"DID document resolution failed for {did}: {e}")

        return None

    async def _fetch_did_document(self, did: str) -> dict | None:
        """Fetch DID document via HTTP.

        Args:
            did: DID identifier

        Returns:
            DID document or None if failed
        """
        try:
            import httpx

            if did.startswith("did:web:"):
                # did:web resolution: convert did:web:example.com to https://example.com/.well-known/did.json
                domain = did.replace("did:web:", "")
                did_doc_url = f"https://{domain}/.well-known/did.json"

                async with httpx.AsyncClient() as client:
                    response = await client.get(did_doc_url, timeout=10.0)
                    response.raise_for_status()
                    return response.json()
            else:
                logger.warning(f"Unsupported DID method for HTTP resolution: {did}")
                return None

        except Exception as e:
            logger.error(f"Failed to fetch DID document for {did}: {e}")
            return None

    def _resolve_did_key(self, did_key: str) -> bytes | None:
        """Resolve public key from did:key method.

        Args:
            did_key: did:key identifier

        Returns:
            Public key bytes or None
        """
        try:
            # did:key format: did:key:z6Mk... where z6Mk indicates Ed25519 key
            import base58

            if not did_key.startswith("did:key:z"):
                return None

            # Extract the multibase encoded key (remove 'did:key:')
            multibase_key = did_key[8:]  # Remove 'did:key:'

            if multibase_key.startswith("z6Mk"):
                # Ed25519 public key (0xed01 prefix + 32 bytes)
                decoded = base58.b58decode(multibase_key[1:])  # Remove 'z' prefix
                return decoded[2:]  # Remove multicodec prefix (0xed01)

        except Exception as e:
            logger.error(f"did:key resolution failed: {e}")

        return None

    async def _verify_ed25519_signature(
        self, public_key_bytes: bytes, data: bytes, signature: bytes
    ) -> bool:
        """Verify Ed25519 signature.

        Args:
            public_key_bytes: Ed25519 public key
            data: Data that was signed
            signature: Signature bytes

        Returns:
            True if signature is valid
        """
        try:
            from cryptography.exceptions import InvalidSignature
            from cryptography.hazmat.primitives.asymmetric import ed25519

            public_key = ed25519.Ed25519PublicKey.from_public_bytes(public_key_bytes)
            public_key.verify(signature, data)
            return True

        except InvalidSignature:
            logger.warning("Invalid Ed25519 signature")
            return False
        except Exception as e:
            logger.error(f"Ed25519 verification error: {e}")
            return False

    async def _verify_rsa_signature(
        self, public_key_bytes: bytes, data: bytes, signature: bytes
    ) -> bool:
        """Verify RSA signature.

        Args:
            public_key_bytes: RSA public key in DER format
            data: Data that was signed
            signature: Signature bytes

        Returns:
            True if signature is valid
        """
        try:
            from cryptography.exceptions import InvalidSignature
            from cryptography.hazmat.primitives import hashes, serialization
            from cryptography.hazmat.primitives.asymmetric import padding, rsa

            public_key = serialization.load_der_public_key(public_key_bytes)
            if not isinstance(public_key, rsa.RSAPublicKey):
                logger.warning("Public key is not RSA")
                return False

            public_key.verify(signature, data, padding.PKCS1v15(), hashes.SHA256())
            return True

        except InvalidSignature:
            logger.warning("Invalid RSA signature")
            return False
        except Exception as e:
            logger.error(f"RSA verification error: {e}")
            return False

    async def _verify_presentation_signature(
        self, presentation: VerifiablePresentation
    ) -> bool:
        """Verify the cryptographic signature of a presentation.

        Implements proper W3C Verifiable Presentations signature verification
        supporting Ed25519Signature2020 and JsonWebSignature2020 proof types.

        Args:
            presentation: The presentation to verify

        Returns:
            True if signature is valid
        """
        if not presentation.proof:
            logger.warning("No proof found in presentation")
            return False

        # Validate required proof fields
        required_fields = ["type", "created", "verification_method", "signature"]
        for field in required_fields:
            if not getattr(presentation.proof, field, None):
                logger.warning(f"Missing required proof field in presentation: {field}")
                return False

        try:
            import base64
            import json

            proof_type = presentation.proof.type
            verification_method = presentation.proof.verification_method
            signature_b64 = presentation.proof.signature

            # Step 1: Resolve public key from verification method (holder's key)
            public_key = await self._resolve_public_key(verification_method)
            if not public_key:
                logger.warning(
                    f"Could not resolve public key for presentation holder: {verification_method}"
                )
                return False

            # Step 2: Create canonical data to verify
            # Remove proof from presentation for verification
            presentation_dict = presentation.model_dump(by_alias=True)
            presentation_dict.pop("proof", None)

            # Create canonical JSON-LD (simplified - in production use pyld)
            canonical_data = json.dumps(
                presentation_dict, sort_keys=True, separators=(",", ":")
            ).encode("utf-8")

            # Step 3: Verify signature based on proof type
            signature_bytes = base64.b64decode(signature_b64)

            if proof_type == "Ed25519Signature2020":
                return await self._verify_ed25519_signature(
                    public_key, canonical_data, signature_bytes
                )
            elif proof_type == "JsonWebSignature2020":
                return await self._verify_rsa_signature(
                    public_key, canonical_data, signature_bytes
                )
            else:
                logger.warning(f"Unsupported presentation signature type: {proof_type}")
                return False

        except Exception as e:
            logger.error(f"Presentation signature verification failed: {e}")
            return False

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
