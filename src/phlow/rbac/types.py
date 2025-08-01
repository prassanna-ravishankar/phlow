"""RBAC-specific types for Phlow authentication."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class CredentialSubject(BaseModel):
    """Subject of a verifiable credential."""

    id: str  # DID of the subject
    role: str | None = None  # Single role
    roles: list[str] | None = None  # Multiple roles

    def get_roles(self) -> list[str]:
        """Get all roles from this credential subject."""
        if self.roles:
            return self.roles
        elif self.role:
            return [self.role]
        return []


class Proof(BaseModel):
    """Cryptographic proof for verifiable credentials."""

    type: str  # e.g., "Ed25519Signature2020"
    created: str  # ISO timestamp
    verification_method: str  # DID URL for verification key
    proof_purpose: str  # e.g., "assertionMethod"
    signature: str  # Base64-encoded signature


class RoleCredential(BaseModel):
    """Verifiable Credential for role assertions."""

    context: list[str] = Field(alias="@context", default=[
        "https://www.w3.org/2018/credentials/v1",
        "https://www.w3.org/2018/credentials/examples/v1"
    ])
    id: str
    type: list[str] = ["VerifiableCredential", "RoleCredential"]
    issuer: str  # DID of the issuer
    issuance_date: str = Field(alias="issuanceDate")  # ISO timestamp
    expiration_date: str | None = Field(alias="expirationDate", default=None)
    credential_subject: CredentialSubject = Field(alias="credentialSubject")
    proof: Proof | None = None

    model_config = {"populate_by_name": True}


class VerifiablePresentation(BaseModel):
    """Verifiable Presentation containing role credentials."""

    context: list[str] = Field(alias="@context", default=[
        "https://www.w3.org/2018/credentials/v1"
    ])
    type: list[str] = ["VerifiablePresentation"]
    verifiable_credential: list[RoleCredential] = Field(alias="verifiableCredential")
    holder: str  # DID of the holder
    proof: Proof | None = None

    model_config = {"populate_by_name": True}


class RoleCredentialRequest(BaseModel):
    """A2A message requesting a role credential."""

    type: str = "role-credential-request"
    required_role: str
    context: str | None = None  # Human-readable context
    nonce: str
    challenge: str | None = None  # For additional security


class RoleCredentialResponse(BaseModel):
    """A2A message responding with a role credential."""

    type: str = "role-credential-response"
    nonce: str
    presentation: VerifiablePresentation | None = None
    error: str | None = None  # If credential not available


class CachedRole(BaseModel):
    """Cached role verification in Supabase."""

    id: str | None = None
    agent_id: str
    role: str
    verified_at: datetime
    expires_at: datetime | None = None
    credential_hash: str
    issuer_did: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class RoleVerificationResult(BaseModel):
    """Result of role credential verification."""

    is_valid: bool
    role: str | None = None
    issuer_did: str | None = None
    expires_at: datetime | None = None
    error_message: str | None = None
    credential_hash: str | None = None
