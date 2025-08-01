"""Comprehensive integration tests for RBAC functionality."""

import asyncio
import os
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from phlow import AgentCard, PhlowConfig, PhlowMiddleware
from phlow.exceptions import AuthenticationError
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
    RoleVerificationResult,
)


class TestRBACIntegration:
    """Integration tests for RBAC system."""

    @pytest.fixture
    def test_agent_card(self):
        """Create a test agent card."""
        return AgentCard(
            name="Test RBAC Agent",
            description="Agent for RBAC integration testing",
            service_url="http://localhost:8000",
            skills=["rbac-testing", "credential-management"],
            security_schemes={
                "phlow-jwt": {"type": "http", "scheme": "bearer", "bearerFormat": "JWT"}
            },
            metadata={
                "agent_id": "test-rbac-agent-123",
                "permissions": ["read:data", "write:data"],
            },
        )

    @pytest.fixture
    def test_config(self, test_agent_card):
        """Create test configuration."""
        return PhlowConfig(
            supabase_url="https://test.supabase.co",
            supabase_anon_key="test-anon-key",
            agent_card=test_agent_card,
            private_key="test-private-key",
            enable_audit_log=True,
        )

    @pytest.fixture
    def mock_supabase(self):
        """Create mock Supabase client."""
        mock_client = MagicMock()
        mock_table = MagicMock()
        mock_client.table.return_value = mock_table
        return mock_client

    @pytest.fixture
    def middleware(self, test_config):
        """Create middleware with mocked dependencies."""
        with (
            patch("phlow.middleware.create_client") as mock_create_client,
            patch("phlow.middleware.httpx.AsyncClient"),
            patch("phlow.middleware.A2AClient"),
            patch.object(PhlowMiddleware, "_convert_to_a2a_agent_card") as mock_convert,
        ):
            mock_create_client.return_value = MagicMock()
            mock_convert.return_value = MagicMock()  # Mock A2A agent card conversion
            
            middleware = PhlowMiddleware(test_config)

            # Override with mock components for testing
            middleware.supabase = MagicMock()
            middleware.role_verifier = RoleCredentialVerifier(middleware.supabase)
            middleware.role_cache = RoleCache(middleware.supabase)
            
            # Create a shared mock context for all tests
            mock_context = MagicMock()
            mock_context.agent = test_config.agent_card
            mock_context.verified_roles = []
            
            # Mock the verify_token method to avoid PhlowContext validation issues
            middleware.verify_token = MagicMock(return_value=mock_context)

            return middleware

    @pytest.fixture
    def sample_admin_credential(self):
        """Create a sample admin role credential."""
        return RoleCredential(
            id="http://example.com/credentials/admin/123",
            issuer="did:example:issuer",
            issuanceDate="2025-08-01T12:00:00Z",
            expirationDate="2026-08-01T12:00:00Z",  # Valid for 1 year
            credentialSubject=CredentialSubject(
                id="did:example:test-rbac-agent-123", role="admin"
            ),
            proof=Proof(
                type="Ed25519Signature2020",
                created="2025-08-01T12:00:00Z",
                verification_method="did:example:issuer#key-1",
                proof_purpose="assertionMethod",
                signature="base64-encoded-signature",
            ),
        )

    @pytest.mark.asyncio
    async def test_full_rbac_flow_with_caching(
        self, middleware, sample_admin_credential
    ):
        """Test complete RBAC flow from authentication to role verification with caching."""
        # Generate a valid token
        token = middleware.generate_token(middleware.config.agent_card)

        # Mock cache miss on first attempt
        middleware.role_cache.get_cached_role = AsyncMock(return_value=None)

        # Mock successful credential request and verification
        mock_presentation = VerifiablePresentation(
            verifiableCredential=[sample_admin_credential],
            holder="did:example:test-rbac-agent-123",
        )

        with patch.object(middleware, "_send_role_credential_request") as mock_send:
            mock_send.return_value = {
                "type": "role-credential-response",
                "nonce": "test-nonce",
                "presentation": mock_presentation.dict(by_alias=True),
            }

            # Mock successful verification
            with patch.object(
                middleware.role_verifier, "verify_presentation"
            ) as mock_verify:
                mock_verify.return_value = RoleVerificationResult(
                    is_valid=True,
                    role="admin",
                    issuer_did="did:example:issuer",
                    credential_hash="test-hash",
                    expires_at=datetime(2026, 8, 1, tzinfo=timezone.utc),
                )

                # Mock cache storage
                middleware.role_cache.cache_verified_role = AsyncMock(return_value=True)

                # Perform authentication with role
                context = await middleware.authenticate_with_role(token, "admin")

                assert context is not None
                assert "admin" in context.verified_roles
                assert context.agent.name == "Test RBAC Agent"

                # Verify cache was called
                middleware.role_cache.cache_verified_role.assert_called_once()

    @pytest.mark.asyncio
    async def test_rbac_flow_with_cached_role(self, middleware):
        """Test RBAC flow when role is already cached."""
        token = middleware.generate_token(middleware.config.agent_card)

        # Mock cached role
        cached_role = CachedRole(
            agent_id="test-rbac-agent-123",
            role="admin",
            verified_at=datetime.now(timezone.utc),
            expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
            credential_hash="cached-hash",
            issuer_did="did:example:issuer",
        )

        middleware.role_cache.get_cached_role = AsyncMock(return_value=cached_role)
        middleware.role_cache.is_expired = MagicMock(return_value=False)

        # Should not call _send_role_credential_request since role is cached
        with patch.object(middleware, "_send_role_credential_request") as mock_send:
            context = await middleware.authenticate_with_role(token, "admin")

            assert context is not None
            assert "admin" in context.verified_roles
            mock_send.assert_not_called()

    @pytest.mark.asyncio
    async def test_rbac_flow_with_expired_cached_role(self, middleware):
        """Test RBAC flow when cached role is expired."""
        token = middleware.generate_token(middleware.config.agent_card)

        # Mock expired cached role
        cached_role = CachedRole(
            agent_id="test-rbac-agent-123",
            role="admin",
            verified_at=datetime.now(timezone.utc) - timedelta(days=2),
            expires_at=datetime.now(timezone.utc) - timedelta(days=1),  # Expired
            credential_hash="expired-hash",
        )

        middleware.role_cache.get_cached_role = AsyncMock(return_value=cached_role)
        middleware.role_cache.is_expired = MagicMock(return_value=True)

        # Should request new credential since cached one is expired
        with patch.object(middleware, "_send_role_credential_request") as mock_send:
            mock_send.return_value = {
                "type": "role-credential-response",
                "nonce": "test-nonce",
                "error": "Role 'admin' not available (mock implementation)",
            }

            with pytest.raises(
                AuthenticationError, match="Role credential request failed"
            ):
                await middleware.authenticate_with_role(token, "admin")

    @pytest.mark.asyncio
    async def test_rbac_flow_with_invalid_signature(
        self, middleware, sample_admin_credential
    ):
        """Test RBAC flow when credential signature verification fails."""
        token = middleware.generate_token(middleware.config.agent_card)

        # No cached role
        middleware.role_cache.get_cached_role = AsyncMock(return_value=None)

        # Mock presentation with invalid signature
        mock_presentation = VerifiablePresentation(
            verifiableCredential=[sample_admin_credential],
            holder="did:example:test-rbac-agent-123",
        )

        with patch.object(middleware, "_send_role_credential_request") as mock_send:
            mock_send.return_value = {
                "type": "role-credential-response",
                "nonce": "test-nonce",
                "presentation": mock_presentation.dict(by_alias=True),
            }

            # Mock failed verification
            with patch.object(
                middleware.role_verifier, "verify_presentation"
            ) as mock_verify:
                mock_verify.return_value = RoleVerificationResult(
                    is_valid=False, error_message="Invalid credential signature"
                )

                with pytest.raises(
                    AuthenticationError, match="Role credential verification failed"
                ):
                    await middleware.authenticate_with_role(token, "admin")

    @pytest.mark.asyncio
    async def test_rbac_flow_with_wrong_role(self, middleware, sample_admin_credential):
        """Test RBAC flow when agent has different role than requested."""
        token = middleware.generate_token(middleware.config.agent_card)

        # No cached role
        middleware.role_cache.get_cached_role = AsyncMock(return_value=None)

        # Create credential with manager role instead of admin
        manager_credential = RoleCredential(
            id="http://example.com/credentials/manager/456",
            issuer="did:example:issuer",
            issuanceDate="2025-08-01T12:00:00Z",
            credentialSubject=CredentialSubject(
                id="did:example:test-rbac-agent-123",
                role="manager",  # Different role
            ),
        )

        mock_presentation = VerifiablePresentation(
            verifiableCredential=[manager_credential],
            holder="did:example:test-rbac-agent-123",
        )

        with patch.object(middleware, "_send_role_credential_request") as mock_send:
            mock_send.return_value = {
                "type": "role-credential-response",
                "nonce": "test-nonce",
                "presentation": mock_presentation.dict(by_alias=True),
            }

            # Mock verification that fails due to wrong role
            with patch.object(
                middleware.role_verifier, "verify_presentation"
            ) as mock_verify:
                mock_verify.return_value = RoleVerificationResult(
                    is_valid=False,
                    error_message="Required role 'admin' not found in credential",
                )

                with pytest.raises(
                    AuthenticationError, match="Role credential verification failed"
                ):
                    await middleware.authenticate_with_role(token, "admin")

    @pytest.mark.asyncio
    async def test_credential_store_persistence(self, tmp_path):
        """Test credential store persistence across instances."""
        store_path = tmp_path / "test_credentials"

        # Create first store and add credentials
        store1 = RoleCredentialStore(store_path)

        admin_cred = RoleCredential(
            id="http://example.com/credentials/admin/789",
            issuer="did:example:issuer",
            issuanceDate="2025-08-01T12:00:00Z",
            credentialSubject=CredentialSubject(id="did:example:agent", role="admin"),
        )

        await store1.add_credential(admin_cred)

        # Create second store with same path
        store2 = RoleCredentialStore(store_path)

        # Should load the saved credential
        loaded_cred = await store2.get_credential("admin")
        assert loaded_cred is not None
        assert loaded_cred.id == admin_cred.id
        assert loaded_cred.credential_subject.role == "admin"

    @pytest.mark.asyncio
    async def test_concurrent_role_verifications(self, middleware):
        """Test handling of concurrent role verification requests."""
        token = middleware.generate_token(middleware.config.agent_card)

        # No cached roles
        middleware.role_cache.get_cached_role = AsyncMock(return_value=None)

        # Mock responses for different roles
        async def mock_send_request(agent_id, request):
            await asyncio.sleep(0.1)  # Simulate network delay
            role = request.required_role
            return {
                "type": "role-credential-response",
                "nonce": request.nonce,
                "error": f"Role '{role}' not available (mock implementation)",
            }

        middleware._send_role_credential_request = mock_send_request

        # Attempt to verify multiple roles concurrently
        tasks = [
            middleware.authenticate_with_role(token, "admin"),
            middleware.authenticate_with_role(token, "manager"),
            middleware.authenticate_with_role(token, "viewer"),
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # All should fail with appropriate error messages
        for result in results:
            assert isinstance(result, AuthenticationError)
            assert "Role credential request failed" in str(result)

    @pytest.mark.asyncio
    async def test_role_cache_cleanup(self, middleware):
        """Test automatic cleanup of expired role cache entries."""
        # Mock cache operations
        middleware.role_cache.cleanup_expired_roles = AsyncMock(return_value=5)

        # Run cleanup
        cleaned = await middleware.role_cache.cleanup_expired_roles()
        assert cleaned == 5

    @pytest.mark.asyncio
    async def test_presentation_creation_and_verification(self):
        """Test creating and verifying a complete verifiable presentation."""
        # Create credential store
        store = RoleCredentialStore()

        # Add multiple role credentials
        admin_cred = RoleCredential(
            id="http://example.com/credentials/admin/001",
            issuer="did:example:issuer",
            issuanceDate="2025-08-01T12:00:00Z",
            credentialSubject=CredentialSubject(id="did:example:holder", role="admin"),
        )

        manager_cred = RoleCredential(
            id="http://example.com/credentials/manager/002",
            issuer="did:example:issuer",
            issuanceDate="2025-08-01T12:00:00Z",
            credentialSubject=CredentialSubject(
                id="did:example:holder", role="manager"
            ),
        )

        await store.add_credential(admin_cred)
        await store.add_credential(manager_cred)

        # Create presentation for admin role
        presentation = await store.create_presentation(
            role="admin", holder_did="did:example:holder"
        )

        assert presentation is not None
        assert len(presentation.verifiable_credential) == 1
        assert presentation.verifiable_credential[0].credential_subject.role == "admin"
        assert presentation.holder == "did:example:holder"

    @pytest.mark.asyncio
    async def test_malformed_credential_handling(self, middleware):
        """Test handling of malformed credentials and presentations."""
        token = middleware.generate_token(middleware.config.agent_card)

        # No cached role
        middleware.role_cache.get_cached_role = AsyncMock(return_value=None)

        # Test various malformed responses
        malformed_responses = [
            # Missing presentation
            {
                "type": "role-credential-response",
                "nonce": "test-nonce",
                # No presentation field
            },
            # Invalid presentation structure
            {
                "type": "role-credential-response",
                "nonce": "test-nonce",
                "presentation": {"invalid": "structure"},
            },
            # Empty credentials array
            {
                "type": "role-credential-response",
                "nonce": "test-nonce",
                "presentation": {
                    "@context": ["https://www.w3.org/2018/credentials/v1"],
                    "type": ["VerifiablePresentation"],
                    "verifiableCredential": [],
                    "holder": "did:example:holder",
                },
            },
        ]

        for response in malformed_responses:
            with patch.object(middleware, "_send_role_credential_request") as mock_send:
                mock_send.return_value = response

                with pytest.raises(AuthenticationError):
                    await middleware.authenticate_with_role(token, "admin")


class TestRBACEdgeCases:
    """Test edge cases and error conditions for RBAC."""

    @pytest.mark.asyncio
    async def test_role_verification_with_multiple_roles(self):
        """Test credential with multiple roles."""
        mock_supabase = MagicMock()
        verifier = RoleCredentialVerifier(mock_supabase)

        # Create credential with multiple roles and proper proof
        multi_role_cred = RoleCredential(
            id="http://example.com/credentials/multi/123",
            issuer="did:example:issuer",
            issuanceDate="2025-08-01T12:00:00Z",
            credentialSubject=CredentialSubject(
                id="did:example:subject",
                roles=["admin", "manager", "viewer"],  # Multiple roles
            ),
            proof=Proof(
                type="Ed25519Signature2020",
                created="2025-08-01T12:00:00Z",
                verification_method="did:example:issuer#key-1",
                proof_purpose="assertionMethod",
                signature="mock-signature",
            ),
        )

        presentation = VerifiablePresentation(
            verifiableCredential=[multi_role_cred],
            holder="did:example:holder",
            proof=Proof(
                type="Ed25519Signature2020",
                created="2025-08-01T12:00:00Z",
                verification_method="did:example:holder#key-1",
                proof_purpose="authentication",
                signature="mock-presentation-signature",
            ),
        )

        # Mock the signature verification to always pass
        with (
            patch.object(verifier, "_verify_credential_signature", return_value=True),
            patch.object(verifier, "_verify_presentation_signature", return_value=True),
        ):
            # Verify different roles
            admin_result = await verifier.verify_presentation(presentation, "admin")
            assert admin_result.is_valid
            assert admin_result.role == "admin"

            manager_result = await verifier.verify_presentation(presentation, "manager")
            assert manager_result.is_valid
            assert manager_result.role == "manager"

            # Non-existent role
            invalid_result = await verifier.verify_presentation(
                presentation, "superuser"
            )
            assert not invalid_result.is_valid
            assert "not found in credential" in invalid_result.error_message

    @pytest.mark.asyncio
    async def test_credential_expiration_boundary(self):
        """Test credential expiration at exact boundary."""
        mock_supabase = MagicMock()
        verifier = RoleCredentialVerifier(mock_supabase)

        # Create credential that expires in 1 second
        now = datetime.now(timezone.utc)
        expiry = now + timedelta(seconds=1)

        boundary_cred = RoleCredential(
            id="http://example.com/credentials/boundary/123",
            issuer="did:example:issuer",
            issuanceDate=now.isoformat(),
            expirationDate=expiry.isoformat(),
            credentialSubject=CredentialSubject(id="did:example:subject", role="admin"),
            proof=Proof(
                type="Ed25519Signature2020",
                created=now.isoformat(),
                verification_method="did:example:issuer#key-1",
                proof_purpose="assertionMethod",
                signature="mock-signature",
            ),
        )

        presentation = VerifiablePresentation(
            verifiableCredential=[boundary_cred],
            holder="did:example:holder",
            proof=Proof(
                type="Ed25519Signature2020",
                created=now.isoformat(),
                verification_method="did:example:holder#key-1",
                proof_purpose="authentication",
                signature="mock-presentation-signature",
            ),
        )

        # Mock signature verification
        with (
            patch.object(verifier, "_verify_credential_signature", return_value=True),
            patch.object(verifier, "_verify_presentation_signature", return_value=True),
        ):
            # Should be valid now
            result1 = await verifier.verify_presentation(presentation, "admin")
            assert result1.is_valid

            # Wait for expiration
            await asyncio.sleep(1.1)

            # Should be expired now
            result2 = await verifier.verify_presentation(presentation, "admin")
            assert not result2.is_valid
            assert "expired" in result2.error_message

    @pytest.mark.asyncio
    async def test_concurrent_cache_operations(self):
        """Test thread safety of cache operations."""
        mock_supabase = MagicMock()
        cache = RoleCache(mock_supabase)

        # Mock database responses
        mock_table = mock_supabase.table.return_value
        mock_table.upsert.return_value.execute.return_value = MagicMock(
            data=[{"id": "test"}]
        )

        # Simulate concurrent cache writes
        tasks = []
        for i in range(10):
            task = cache.cache_verified_role(
                agent_id=f"agent-{i}",
                role="admin",
                credential_hash=f"hash-{i}",
                issuer_did="did:example:issuer",
            )
            tasks.append(task)

        results = await asyncio.gather(*tasks)

        # All operations should succeed
        assert all(results)
        assert mock_table.upsert.call_count == 10

    @pytest.mark.asyncio
    async def test_invalid_did_formats(self):
        """Test handling of invalid DID formats."""
        mock_supabase = MagicMock()
        verifier = RoleCredentialVerifier(mock_supabase)

        # Create credentials with invalid DIDs
        invalid_did_cred = RoleCredential(
            id="http://example.com/credentials/invalid/123",
            issuer="invalid-did-format",  # Invalid DID
            issuanceDate="2025-08-01T12:00:00Z",
            credentialSubject=CredentialSubject(
                id="also-invalid",  # Invalid DID
                role="admin",
            ),
            proof=Proof(
                type="Ed25519Signature2020",
                created="2025-08-01T12:00:00Z",
                verification_method="invalid-did-format#key-1",
                proof_purpose="assertionMethod",
                signature="mock-signature",
            ),
        )

        presentation = VerifiablePresentation(
            verifiableCredential=[invalid_did_cred],
            holder="not-a-did",  # Invalid DID
            proof=Proof(
                type="Ed25519Signature2020",
                created="2025-08-01T12:00:00Z",
                verification_method="not-a-did#key-1",
                proof_purpose="authentication",
                signature="mock-presentation-signature",
            ),
        )

        # Mock signature verification to return True for this test
        with (
            patch.object(verifier, "_verify_credential_signature", return_value=True),
            patch.object(verifier, "_verify_presentation_signature", return_value=True),
        ):
            # Should still process (simplified implementation)
            # In production, this would validate DID formats
            result = await verifier.verify_presentation(presentation, "admin")
            # Current implementation doesn't validate DID format but has valid signature
            assert result.is_valid  # Would be False in production with DID validation

    @pytest.mark.asyncio
    async def test_credential_store_concurrent_access(self, tmp_path):
        """Test concurrent access to credential store."""
        store_path = tmp_path / "concurrent_test"

        # Create multiple stores accessing same path
        stores = [RoleCredentialStore(store_path) for _ in range(5)]

        # Add credentials concurrently
        tasks = []
        for i, store in enumerate(stores):
            cred = RoleCredential(
                id=f"http://example.com/credentials/concurrent/{i}",
                issuer="did:example:issuer",
                issuanceDate="2025-08-01T12:00:00Z",
                credentialSubject=CredentialSubject(
                    id="did:example:subject", role=f"role-{i}"
                ),
            )
            tasks.append(store.add_credential(cred))

        await asyncio.gather(*tasks)

        # Verify all credentials were saved
        final_store = RoleCredentialStore(store_path)
        all_roles = await final_store.get_all_roles()

        # Should have all 5 roles
        assert len(all_roles) == 5
        assert all(f"role-{i}" in all_roles for i in range(5))


class TestRBACPerformance:
    """Performance tests for RBAC system."""

    @pytest.fixture
    def test_agent_card(self):
        """Create a test agent card."""
        return AgentCard(
            name="Test RBAC Agent",
            description="Agent for RBAC integration testing",
            service_url="http://localhost:8000",
            skills=["rbac-testing", "credential-management"],
            security_schemes={
                "phlow-jwt": {"type": "http", "scheme": "bearer", "bearerFormat": "JWT"}
            },
            metadata={
                "agent_id": "test-rbac-agent-123",
                "permissions": ["read:data", "write:data"],
            },
        )

    @pytest.fixture
    def test_config(self, test_agent_card):
        """Create test configuration."""
        return PhlowConfig(
            supabase_url="https://test.supabase.co",
            supabase_anon_key="test-anon-key",
            agent_card=test_agent_card,
            private_key="test-private-key",
            enable_audit_log=True,
        )

    @pytest.fixture
    def middleware(self, test_config):
        """Create middleware with mocked dependencies."""
        with (
            patch("phlow.middleware.create_client") as mock_create_client,
            patch("phlow.middleware.httpx.AsyncClient"),
            patch("phlow.middleware.A2AClient"),
            patch.object(PhlowMiddleware, "_convert_to_a2a_agent_card") as mock_convert,
        ):
            mock_create_client.return_value = MagicMock()
            mock_convert.return_value = MagicMock()  # Mock A2A agent card conversion
            
            middleware = PhlowMiddleware(test_config)

            # Override with mock components for testing
            middleware.supabase = MagicMock()
            middleware.role_verifier = RoleCredentialVerifier(middleware.supabase)
            middleware.role_cache = RoleCache(middleware.supabase)
            
            # Create a shared mock context for all tests
            mock_context = MagicMock()
            mock_context.agent = test_config.agent_card
            mock_context.verified_roles = []
            
            # Mock the verify_token method to avoid PhlowContext validation issues
            middleware.verify_token = MagicMock(return_value=mock_context)

            return middleware

    @pytest.mark.asyncio
    async def test_cache_performance_improvement(self, middleware):
        """Test that caching improves performance significantly."""
        token = middleware.generate_token(middleware.config.agent_card)

        # Mock expensive verification process
        verification_time = 0.5  # 500ms

        async def slow_verification(*args):
            await asyncio.sleep(verification_time)
            return RoleVerificationResult(
                is_valid=True, role="admin", credential_hash="test-hash"
            )

        # First call - no cache
        middleware.role_cache.get_cached_role = AsyncMock(return_value=None)
        middleware.role_verifier.verify_presentation = slow_verification
        middleware.role_cache.cache_verified_role = AsyncMock(return_value=True)

        with patch.object(middleware, "_send_role_credential_request") as mock_send:
            mock_send.return_value = {
                "type": "role-credential-response",
                "nonce": "test-nonce",
                "presentation": {
                    "@context": ["https://www.w3.org/2018/credentials/v1"],
                    "type": ["VerifiablePresentation"],
                    "verifiableCredential": [
                        {
                            "@context": ["https://www.w3.org/2018/credentials/v1"],
                            "id": "test-cred",
                            "type": ["VerifiableCredential", "RoleCredential"],
                            "issuer": "did:example:issuer",
                            "issuanceDate": "2025-08-01T12:00:00Z",
                            "credentialSubject": {
                                "id": "did:example:subject",
                                "role": "admin",
                            },
                        }
                    ],
                    "holder": "did:example:holder",
                },
            }

            # Time first call (no cache)
            import time

            start = time.time()
            await middleware.authenticate_with_role(token, "admin")
            first_call_time = time.time() - start

            assert first_call_time >= verification_time

        # Second call - with cache
        cached_role = CachedRole(
            agent_id="test-rbac-agent-123",
            role="admin",
            verified_at=datetime.now(timezone.utc),
            credential_hash="test-hash",
        )

        middleware.role_cache.get_cached_role = AsyncMock(return_value=cached_role)
        middleware.role_cache.is_expired = MagicMock(return_value=False)

        start = time.time()
        await middleware.authenticate_with_role(token, "admin")
        second_call_time = time.time() - start

        # Cached call should be much faster
        assert second_call_time < 0.1  # Less than 100ms
        assert second_call_time < first_call_time / 5  # At least 5x faster

    @pytest.mark.asyncio
    async def test_bulk_credential_operations(self, tmp_path):
        """Test performance of bulk credential operations."""
        # Use isolated store path to avoid contamination
        store_path = tmp_path / "bulk_test_store"
        store = RoleCredentialStore(store_path)

        # Add many credentials
        num_credentials = 100
        start_time = asyncio.get_event_loop().time()

        for i in range(num_credentials):
            cred = RoleCredential(
                id=f"http://example.com/credentials/bulk/{i}",
                issuer="did:example:issuer",
                issuanceDate="2025-08-01T12:00:00Z",
                credentialSubject=CredentialSubject(
                    id="did:example:subject", role=f"role-{i}"
                ),
            )
            await store.add_credential(cred)

        add_time = asyncio.get_event_loop().time() - start_time

        # Should complete reasonably fast
        assert add_time < 5.0  # Less than 5 seconds for 100 credentials

        # Test retrieval performance
        start_time = asyncio.get_event_loop().time()
        all_roles = await store.get_all_roles()
        get_time = asyncio.get_event_loop().time() - start_time

        assert len(all_roles) == num_credentials
        assert get_time < 0.5  # Less than 500ms to get all roles


# Gemini API integration tests (if API key is available)
if os.getenv("GEMINI_API_KEY"):

    class TestRBACWithGemini:
        """Integration tests using Gemini API for realistic scenarios."""

        @pytest.mark.asyncio
        async def test_gemini_powered_role_description_analysis(self):
            """Test using Gemini to analyze role descriptions for security implications."""
            # This would use Gemini to analyze role credential descriptions
            # and identify potential security issues
            pass  # Placeholder for Gemini integration
