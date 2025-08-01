"""Tests for RBAC functionality."""

from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest

from phlow.rbac import (
    RoleCache,
    RoleCredential,
    RoleCredentialStore,
    RoleCredentialVerifier,
    VerifiablePresentation,
)
from phlow.rbac.types import (
    CachedRole,
    CredentialSubject,
    Proof,
    RoleCredentialRequest,
    RoleCredentialResponse,
)


class TestRoleCredential:
    """Test RoleCredential model."""

    def test_role_credential_creation(self):
        """Test creating a valid role credential."""
        credential = RoleCredential(
            id="http://example.com/credentials/123",
            issuer="did:example:issuer",
            issuanceDate="2025-08-01T12:00:00Z",
            credentialSubject=CredentialSubject(
                id="did:example:subject",
                role="admin"
            )
        )

        assert credential.id == "http://example.com/credentials/123"
        assert credential.issuer == "did:example:issuer"
        assert credential.credential_subject.role == "admin"
        assert "RoleCredential" in credential.type

    def test_role_credential_with_multiple_roles(self):
        """Test role credential with multiple roles."""
        credential = RoleCredential(
            id="http://example.com/credentials/123",
            issuer="did:example:issuer",
            issuanceDate="2025-08-01T12:00:00Z",
            credentialSubject=CredentialSubject(
                id="did:example:subject",
                roles=["admin", "manager"]
            )
        )

        roles = credential.credential_subject.get_roles()
        assert "admin" in roles
        assert "manager" in roles
        assert len(roles) == 2

    def test_role_credential_with_expiration(self):
        """Test role credential with expiration date."""
        credential = RoleCredential(
            id="http://example.com/credentials/123",
            issuer="did:example:issuer",
            issuanceDate="2025-08-01T12:00:00Z",
            expirationDate="2025-12-31T23:59:59Z",
            credentialSubject=CredentialSubject(
                id="did:example:subject",
                role="admin"
            )
        )

        assert credential.expiration_date == "2025-12-31T23:59:59Z"

    def test_role_credential_json_serialization(self):
        """Test JSON serialization with aliases."""
        credential = RoleCredential(
            id="http://example.com/credentials/123",
            issuer="did:example:issuer",
            issuanceDate="2025-08-01T12:00:00Z",
            credentialSubject=CredentialSubject(
                id="did:example:subject",
                role="admin"
            )
        )

        json_data = credential.dict(by_alias=True)
        assert "@context" in json_data
        assert "credentialSubject" in json_data
        assert "issuanceDate" in json_data


class TestVerifiablePresentation:
    """Test VerifiablePresentation model."""

    def test_verifiable_presentation_creation(self):
        """Test creating a verifiable presentation."""
        credential = RoleCredential(
            id="http://example.com/credentials/123",
            issuer="did:example:issuer",
            issuanceDate="2025-08-01T12:00:00Z",
            credentialSubject=CredentialSubject(
                id="did:example:subject",
                role="admin"
            )
        )

        presentation = VerifiablePresentation(
            verifiableCredential=[credential],
            holder="did:example:holder"
        )

        assert presentation.holder == "did:example:holder"
        assert len(presentation.verifiable_credential) == 1
        assert presentation.verifiable_credential[0].credential_subject.role == "admin"


class TestRoleCredentialVerifier:
    """Test RoleCredentialVerifier class."""

    @pytest.fixture
    def mock_supabase(self):
        """Mock Supabase client."""
        return MagicMock()

    @pytest.fixture
    def verifier(self, mock_supabase):
        """Create RoleCredentialVerifier instance."""
        return RoleCredentialVerifier(mock_supabase)

    @pytest.fixture
    def sample_credential(self):
        """Create a sample role credential."""
        return RoleCredential(
            id="http://example.com/credentials/123",
            issuer="did:example:issuer",
            issuanceDate="2025-08-01T12:00:00Z",
            credentialSubject=CredentialSubject(
                id="did:example:subject",
                role="admin"
            ),
            proof=Proof(
                type="Ed25519Signature2020",
                created="2025-08-01T12:00:00Z",
                verification_method="did:example:issuer#key-1",
                proof_purpose="assertionMethod",
                signature="base64-encoded-signature"
            )
        )

    @pytest.fixture
    def sample_presentation(self, sample_credential):
        """Create a sample verifiable presentation."""
        return VerifiablePresentation(
            verifiableCredential=[sample_credential],
            holder="did:example:holder",
            proof=Proof(
                type="Ed25519Signature2020",
                created="2025-08-01T12:00:00Z",
                verification_method="did:example:holder#key-1",
                proof_purpose="authentication",
                signature="base64-encoded-signature"
            )
        )

    @pytest.mark.asyncio
    async def test_verify_valid_presentation(self, verifier, sample_presentation):
        """Test verifying a valid presentation."""
        result = await verifier.verify_presentation(sample_presentation, "admin")

        assert result.is_valid
        assert result.role == "admin"
        assert result.issuer_did == "did:example:issuer"
        assert result.credential_hash is not None

    @pytest.mark.asyncio
    async def test_verify_presentation_no_credentials(self, verifier):
        """Test verifying presentation with no credentials."""
        presentation = VerifiablePresentation(
            verifiableCredential=[],
            holder="did:example:holder"
        )

        result = await verifier.verify_presentation(presentation, "admin")

        assert not result.is_valid
        assert "No credentials in presentation" in result.error_message

    @pytest.mark.asyncio
    async def test_verify_presentation_wrong_role(self, verifier, sample_presentation):
        """Test verifying presentation with wrong role."""
        result = await verifier.verify_presentation(sample_presentation, "manager")

        assert not result.is_valid
        assert "not found in credential" in result.error_message

    @pytest.mark.asyncio
    async def test_verify_expired_credential(self, verifier, mock_supabase):
        """Test verifying expired credential."""
        # Create an expired credential
        expired_credential = RoleCredential(
            id="http://example.com/credentials/123",
            issuer="did:example:issuer",
            issuanceDate="2025-08-01T12:00:00Z",
            expirationDate="2025-08-01T13:00:00Z",  # Expired
            credentialSubject=CredentialSubject(
                id="did:example:subject",
                role="admin"
            ),
            proof=Proof(
                type="Ed25519Signature2020",
                created="2025-08-01T12:00:00Z",
                verification_method="did:example:issuer#key-1",
                proof_purpose="assertionMethod",
                signature="base64-encoded-signature"
            )
        )

        presentation = VerifiablePresentation(
            verifiableCredential=[expired_credential],
            holder="did:example:holder"
        )

        result = await verifier.verify_presentation(presentation, "admin")

        assert not result.is_valid
        assert "expired" in result.error_message


class TestRoleCache:
    """Test RoleCache class."""

    @pytest.fixture
    def mock_supabase(self):
        """Mock Supabase client."""
        mock_client = MagicMock()
        mock_table = MagicMock()
        mock_client.table.return_value = mock_table
        return mock_client

    @pytest.fixture
    def cache(self, mock_supabase):
        """Create RoleCache instance."""
        return RoleCache(mock_supabase)

    @pytest.mark.asyncio
    async def test_cache_verified_role(self, cache, mock_supabase):
        """Test caching a verified role."""
        mock_table = mock_supabase.table.return_value
        mock_result = MagicMock()
        mock_result.data = [{"id": "test-id"}]
        mock_table.upsert.return_value.execute.return_value = mock_result

        result = await cache.cache_verified_role(
            agent_id="test-agent",
            role="admin",
            credential_hash="test-hash",
            issuer_did="did:example:issuer"
        )

        assert result is True
        mock_table.upsert.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_cached_role(self, cache, mock_supabase):
        """Test retrieving cached role."""
        mock_table = mock_supabase.table.return_value
        mock_result = MagicMock()
        mock_result.data = [{
            "id": "test-id",
            "agent_id": "test-agent",
            "role": "admin",
            "verified_at": "2025-08-01T12:00:00+00:00",
            "expires_at": None,
            "credential_hash": "test-hash",
            "issuer_did": "did:example:issuer",
            "metadata": {}
        }]
        mock_table.select.return_value.eq.return_value.eq.return_value.execute.return_value = mock_result

        cached_role = await cache.get_cached_role("test-agent", "admin")

        assert cached_role is not None
        assert cached_role.agent_id == "test-agent"
        assert cached_role.role == "admin"
        assert cached_role.credential_hash == "test-hash"

    @pytest.mark.asyncio
    async def test_get_cached_role_not_found(self, cache, mock_supabase):
        """Test retrieving non-existent cached role."""
        mock_table = mock_supabase.table.return_value
        mock_result = MagicMock()
        mock_result.data = []
        mock_table.select.return_value.eq.return_value.eq.return_value.execute.return_value = mock_result

        cached_role = await cache.get_cached_role("test-agent", "admin")

        assert cached_role is None

    def test_is_expired_with_no_expiry(self, cache):
        """Test expiry check with no expiration date."""
        cached_role = CachedRole(
            agent_id="test-agent",
            role="admin",
            verified_at=datetime.now(timezone.utc),
            credential_hash="test-hash"
        )

        assert not cache.is_expired(cached_role)

    def test_is_expired_with_future_expiry(self, cache):
        """Test expiry check with future expiration."""
        cached_role = CachedRole(
            agent_id="test-agent",
            role="admin",
            verified_at=datetime.now(timezone.utc),
            expires_at=datetime(2030, 1, 1, tzinfo=timezone.utc),
            credential_hash="test-hash"
        )

        assert not cache.is_expired(cached_role)

    def test_is_expired_with_past_expiry(self, cache):
        """Test expiry check with past expiration."""
        cached_role = CachedRole(
            agent_id="test-agent",
            role="admin",
            verified_at=datetime.now(timezone.utc),
            expires_at=datetime(2020, 1, 1, tzinfo=timezone.utc),
            credential_hash="test-hash"
        )

        assert cache.is_expired(cached_role)


class TestRoleCredentialStore:
    """Test RoleCredentialStore class."""

    @pytest.fixture
    def temp_storage_path(self, tmp_path):
        """Create temporary storage path."""
        return tmp_path / "credentials"

    @pytest.fixture
    def store(self, temp_storage_path):
        """Create RoleCredentialStore instance."""
        return RoleCredentialStore(temp_storage_path)

    @pytest.fixture
    def sample_credential(self):
        """Create a sample role credential."""
        return RoleCredential(
            id="http://example.com/credentials/123",
            issuer="did:example:issuer",
            issuanceDate="2025-08-01T12:00:00Z",
            credentialSubject=CredentialSubject(
                id="did:example:subject",
                role="admin"
            )
        )

    @pytest.mark.asyncio
    async def test_add_and_get_credential(self, store, sample_credential):
        """Test adding and retrieving credentials."""
        await store.add_credential(sample_credential)

        retrieved = await store.get_credential("admin")
        assert retrieved is not None
        assert retrieved.credential_subject.role == "admin"

    @pytest.mark.asyncio
    async def test_has_role(self, store, sample_credential):
        """Test checking if store has role."""
        await store.add_credential(sample_credential)

        assert await store.has_role("admin")
        assert not await store.has_role("manager")

    @pytest.mark.asyncio
    async def test_get_all_roles(self, store, sample_credential):
        """Test getting all available roles."""
        await store.add_credential(sample_credential)

        roles = await store.get_all_roles()
        assert "admin" in roles
        assert len(roles) == 1

    @pytest.mark.asyncio
    async def test_remove_credential(self, store, sample_credential):
        """Test removing credentials."""
        await store.add_credential(sample_credential)

        assert await store.has_role("admin")

        removed = await store.remove_credential("admin")
        assert removed
        assert not await store.has_role("admin")

    @pytest.mark.asyncio
    async def test_create_presentation(self, store, sample_credential):
        """Test creating verifiable presentation."""
        await store.add_credential(sample_credential)

        presentation = await store.create_presentation(
            role="admin",
            holder_did="did:example:holder"
        )

        assert presentation is not None
        assert presentation.holder == "did:example:holder"
        assert len(presentation.verifiable_credential) == 1
        assert presentation.verifiable_credential[0].credential_subject.role == "admin"

    @pytest.mark.asyncio
    async def test_create_presentation_missing_role(self, store):
        """Test creating presentation for missing role."""
        presentation = await store.create_presentation(
            role="admin",
            holder_did="did:example:holder"
        )

        assert presentation is None

    @pytest.mark.asyncio
    async def test_persistence(self, store, sample_credential, temp_storage_path):
        """Test credential persistence across store instances."""
        # Add credential and save
        await store.add_credential(sample_credential)

        # Create new store instance with same path
        new_store = RoleCredentialStore(temp_storage_path)

        # Should load the saved credential
        retrieved = await new_store.get_credential("admin")
        assert retrieved is not None
        assert retrieved.credential_subject.role == "admin"


class TestRoleCredentialMessages:
    """Test role credential request/response messages."""

    def test_role_credential_request(self):
        """Test creating role credential request."""
        request = RoleCredentialRequest(
            required_role="admin",
            context="Access requires admin role",
            nonce="test-nonce-123"
        )

        assert request.type == "role-credential-request"
        assert request.required_role == "admin"
        assert request.nonce == "test-nonce-123"

    def test_role_credential_response_success(self):
        """Test successful role credential response."""
        credential = RoleCredential(
            id="http://example.com/credentials/123",
            issuer="did:example:issuer",
            issuanceDate="2025-08-01T12:00:00Z",
            credentialSubject=CredentialSubject(
                id="did:example:subject",
                role="admin"
            )
        )

        presentation = VerifiablePresentation(
            verifiableCredential=[credential],
            holder="did:example:holder"
        )

        response = RoleCredentialResponse(
            nonce="test-nonce-123",
            presentation=presentation
        )

        assert response.type == "role-credential-response"
        assert response.nonce == "test-nonce-123"
        assert response.presentation is not None
        assert response.error is None

    def test_role_credential_response_error(self):
        """Test error role credential response."""
        response = RoleCredentialResponse(
            nonce="test-nonce-123",
            error="Role 'admin' not available"
        )

        assert response.type == "role-credential-response"
        assert response.nonce == "test-nonce-123"
        assert response.presentation is None
        assert response.error == "Role 'admin' not available"
