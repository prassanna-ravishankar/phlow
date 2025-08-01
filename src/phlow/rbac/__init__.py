"""RBAC (Role-Based Access Control) module for Phlow."""

from .cache import RoleCache
from .store import RoleCredentialStore
from .types import (
    CachedRole,
    CredentialSubject,
    Proof,
    RoleCredential,
    RoleCredentialRequest,
    RoleCredentialResponse,
    RoleVerificationResult,
    VerifiablePresentation,
)
from .verifier import RoleCredentialVerifier

__all__ = [
    # Core types
    "RoleCredential",
    "VerifiablePresentation",
    "CredentialSubject",
    "Proof",
    "CachedRole",
    "RoleVerificationResult",
    # Message types
    "RoleCredentialRequest",
    "RoleCredentialResponse",
    # Core components
    "RoleCredentialVerifier",
    "RoleCache",
    "RoleCredentialStore",
]
