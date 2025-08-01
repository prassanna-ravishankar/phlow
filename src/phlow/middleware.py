"""Phlow middleware - A2A Protocol extension with Supabase integration."""

import secrets
import string
from datetime import datetime, timedelta, timezone
from typing import Any

import httpx
import jwt
from a2a.client import A2AClient
from a2a.types import AgentCard as A2AAgentCard
from a2a.types import Task
from supabase import create_client

from .exceptions import AuthenticationError, ConfigurationError
from .rbac import RoleCache, RoleCredentialVerifier
from .rbac.types import (
    RoleCredentialRequest,
    RoleCredentialResponse,
)
from .types import AgentCard, PhlowConfig, PhlowContext


class PhlowMiddleware:
    """Phlow middleware for A2A Protocol with Supabase features."""

    def __init__(self, config: PhlowConfig):
        """Initialize Phlow middleware.

        Args:
            config: Phlow configuration
        """
        self.config = config
        self.supabase = create_client(config.supabase_url, config.supabase_anon_key)

        # Initialize A2A client with httpx client and agent card
        self.httpx_client = httpx.AsyncClient()
        self.a2a_client = A2AClient(
            httpx_client=self.httpx_client,
            agent_card=self._convert_to_a2a_agent_card(config.agent_card),
        )

        # Initialize RBAC components
        self.role_verifier = RoleCredentialVerifier(self.supabase)
        self.role_cache = RoleCache(self.supabase)

        # Validate configuration
        if not config.supabase_url or not config.supabase_anon_key:
            raise ConfigurationError("Supabase URL and anon key are required")

    def _convert_to_a2a_agent_card(self, agent_card: AgentCard) -> A2AAgentCard:
        """Convert Phlow AgentCard to A2A AgentCard."""
        return A2AAgentCard(
            name=agent_card.name,
            description=agent_card.description,
            url=agent_card.service_url,  # service_url -> url
            skills=agent_card.skills,
            security_schemes=agent_card.security_schemes,
            # metadata is not a direct field in A2A AgentCard
        )

    def verify_token(self, token: str) -> PhlowContext:
        """Verify JWT token and return context.

        Args:
            token: JWT token to verify

        Returns:
            PhlowContext with agent info and supabase client

        Raises:
            AuthenticationError: If token is invalid
        """
        try:
            # Decode token (in real implementation, use proper key validation)
            decoded = jwt.decode(
                token,
                self.config.private_key,
                algorithms=["RS256", "HS256"],
                options={"verify_signature": False},  # For testing only
            )

            # Create context with A2A integration
            context = PhlowContext(
                agent=self.config.agent_card,
                token=token,
                claims=decoded,
                supabase=self.supabase,
                a2a_client=self.a2a_client,
            )

            return context

        except jwt.InvalidTokenError as e:
            raise AuthenticationError(f"Invalid token: {str(e)}")

    async def authenticate_with_role(self, token: str, required_role: str) -> PhlowContext:
        """Authenticate and verify role credentials.

        Args:
            token: JWT token
            required_role: The role string to verify (e.g., 'admin')

        Returns:
            PhlowContext with verified role information

        Raises:
            AuthenticationError: If authentication or role verification fails
        """
        # 1. Perform standard Phlow authentication first
        context = self.verify_token(token)

        # 2. Get agent ID from context
        agent_id = context.agent.metadata.get('agent_id') if context.agent.metadata else None
        if not agent_id:
            raise AuthenticationError("Agent ID not found in token")

        # 3. Check cache for previously verified role
        cached_role = await self.role_cache.get_cached_role(agent_id, required_role)

        if cached_role and not self.role_cache.is_expired(cached_role):
            context.verified_roles = [required_role]
            return context

        # 4. Request role credential via A2A messaging
        try:
            nonce = self._generate_nonce()
            request_message = RoleCredentialRequest(
                required_role=required_role,
                context=f"Access requires '{required_role}' role",
                nonce=nonce
            )

            # Send A2A message to request role credential
            # Note: This is a simplified implementation
            # In practice, this would use the A2A client's messaging system
            role_response_data = await self._send_role_credential_request(
                agent_id, request_message
            )

            if not role_response_data:
                raise AuthenticationError(f"No response received for role '{required_role}' request")

            role_response = RoleCredentialResponse(**role_response_data)

            # 5. Verify the credential
            if role_response.presentation and not role_response.error:
                verification_result = await self.role_verifier.verify_presentation(
                    role_response.presentation, required_role
                )

                if verification_result.is_valid:
                    # 6. Cache the verified role
                    await self.role_cache.cache_verified_role(
                        agent_id=agent_id,
                        role=required_role,
                        credential_hash=verification_result.credential_hash,
                        issuer_did=verification_result.issuer_did,
                        expires_at=verification_result.expires_at
                    )

                    context.verified_roles = [required_role]
                    return context
                else:
                    raise AuthenticationError(
                        f"Role credential verification failed: {verification_result.error_message}"
                    )
            else:
                error_msg = role_response.error or "No valid presentation provided"
                raise AuthenticationError(f"Role credential request failed: {error_msg}")

        except Exception as e:
            if isinstance(e, AuthenticationError):
                raise
            raise AuthenticationError(f"Error during role verification: {str(e)}")

    async def _send_role_credential_request(
        self,
        agent_id: str,
        request: RoleCredentialRequest
    ) -> dict | None:
        """Send role credential request via A2A messaging.

        This is a simplified implementation. In production, this would use
        the A2A client to send messages to the specific agent.

        Args:
            agent_id: Target agent ID
            request: Role credential request

        Returns:
            Response data or None if failed
        """
        try:
            # TODO: Implement actual A2A messaging
            # For now, return a mock response
            # In production, this would:
            # 1. Resolve agent's A2A endpoint
            # 2. Send the request message
            # 3. Wait for response with timeout
            # 4. Return the response data

            # Mock response for testing
            return {
                "type": "role-credential-response",
                "nonce": request.nonce,
                "error": f"Role '{request.required_role}' not available"
            }

        except Exception as e:
            print(f"Error sending role credential request: {e}")
            return None

    def _generate_nonce(self) -> str:
        """Generate a random nonce for role credential requests.

        Returns:
            Random alphanumeric string
        """
        return ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(16))

    def get_a2a_client(self) -> Any | None:
        """Get the A2A client instance."""
        return self.a2a_client

    def get_supabase_client(self):
        """Get the Supabase client instance."""
        return self.supabase

    def generate_rls_policy(self, agent_id: str, permissions: list) -> str:
        """Generate RLS policy for Supabase.

        Args:
            agent_id: Agent ID
            permissions: List of required permissions

        Returns:
            SQL policy string
        """
        permission_checks = " OR ".join(
            [f"auth.jwt() ->> 'permissions' ? '{p}'" for p in permissions]
        )

        return f"""
            CREATE POLICY "{agent_id}_policy" ON your_table
            FOR ALL
            TO authenticated
            USING (
                auth.jwt() ->> 'sub' = '{agent_id}'
                AND ({permission_checks})
            );
        """

    def generate_token(self, agent_card: AgentCard) -> str:
        """Generate JWT token for agent.

        Args:
            agent_card: Agent card to generate token for

        Returns:
            JWT token string
        """
        payload = {
            "sub": agent_card.metadata.get("agent_id") if agent_card.metadata else None,
            "name": agent_card.name,
            "iat": datetime.now(timezone.utc),
            "exp": datetime.now(timezone.utc) + timedelta(hours=1),
        }

        return jwt.encode(payload, self.config.private_key, algorithm="HS256")

    def send_message(self, target_agent_id: str, message: str) -> Task:
        """Send A2A message to another agent.

        Args:
            target_agent_id: Target agent ID
            message: Message content

        Returns:
            Task object for tracking message
        """
        # This would use the A2A client to send messages
        # For now, return a mock task
        return Task(
            id=f"task-{datetime.now(timezone.utc).isoformat()}",
            # A2A Task doesn't have agent_id, status, or messages fields directly
            # These would be handled differently in the actual A2A protocol
        )

    def resolve_agent(self, agent_id: str) -> A2AAgentCard | None:
        """Resolve agent card from A2A network or Supabase.

        Args:
            agent_id: Agent ID to resolve

        Returns:
            A2AAgentCard if found, None otherwise
        """
        # First try to resolve from Supabase
        try:
            result = (
                self.supabase.table("agent_cards")
                .select("*")
                .eq("agent_id", agent_id)
                .single()
                .execute()
            )
            if result.data:
                data = result.data
                return A2AAgentCard(
                    name=data["name"],
                    description=data.get("description", ""),
                    service_url=data.get("service_url", ""),
                    skills=data.get("skills", []),
                    security_schemes=data.get("security_schemes", {}),
                    metadata=data.get("metadata", {}),
                )
        except Exception:
            pass

        # Fallback to A2A network resolution
        # This would use the A2A client to resolve from network
        return None

    async def log_auth_event(
        self, agent_id: str, success: bool, metadata: dict | None = None
    ):
        """Log authentication event to Supabase.

        Args:
            agent_id: Agent ID
            success: Whether authentication succeeded
            metadata: Additional metadata
        """
        if not self.config.enable_audit_log:
            return

        try:
            await (
                self.supabase.table("auth_audit_log")
                .insert(
                    {
                        "agent_id": agent_id,
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "event_type": "authentication",
                        "success": success,
                        "metadata": metadata or {},
                    }
                )
                .execute()
            )
        except Exception as e:
            # Log error but don't fail authentication
            print(f"Failed to log auth event: {e}")

    def register_agent_with_supabase(self, agent_card: AgentCard) -> None:
        """Register agent card with Supabase for local resolution.

        Args:
            agent_card: Agent card to register
        """
        try:
            self.supabase.table("agent_cards").upsert(
                {
                    "agent_id": (
                        agent_card.metadata.get("agent_id")
                        if agent_card.metadata
                        else None
                    ),
                    "name": agent_card.name,
                    "description": agent_card.description,
                    "service_url": agent_card.service_url,
                    "schema_version": agent_card.schema_version,
                    "skills": agent_card.skills,
                    "security_schemes": agent_card.security_schemes,
                    "metadata": agent_card.metadata,
                    "created_at": datetime.now(timezone.utc).isoformat(),
                }
            ).execute()
        except Exception as e:
            raise ConfigurationError(f"Failed to register agent: {e}")

    def authenticate(self):
        """Return authentication middleware function.

        For use with web frameworks like FastAPI or Flask.
        This would need framework-specific implementation.
        """

        def middleware(request):
            # This would be implemented for specific frameworks
            # For now, return a placeholder
            auth_header = getattr(request, "headers", {}).get("authorization", "")
            if not auth_header.startswith("Bearer "):
                raise AuthenticationError("Missing or invalid authorization header")

            token = auth_header[7:]
            context = self.verify_token(token)

            # Attach context to request
            request.phlow = context
            return request

        return middleware
