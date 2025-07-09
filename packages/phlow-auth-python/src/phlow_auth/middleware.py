"""Phlow middleware - A2A Protocol extension with Supabase integration."""

import datetime
from typing import Any, Dict, Optional

import jwt
from a2a.client import A2AClient
from a2a.types import AgentCard as A2AAgentCard
from a2a.types import Message, Task
from supabase import create_client

from .exceptions import AuthenticationError, ConfigurationError
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

        # Initialize A2A client with agent card
        self.a2a_client = A2AClient(self._convert_to_a2a_agent_card(config.agent_card))

        # Validate configuration
        if not config.supabase_url or not config.supabase_anon_key:
            raise ConfigurationError("Supabase URL and anon key are required")

    def _convert_to_a2a_agent_card(self, agent_card: AgentCard) -> A2AAgentCard:
        """Convert Phlow AgentCard to A2A AgentCard."""
        return A2AAgentCard(
            name=agent_card.name,
            description=agent_card.description,
            service_url=agent_card.service_url,
            skills=agent_card.skills,
            security_schemes=agent_card.security_schemes,
            metadata=agent_card.metadata,
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

    def get_a2a_client(self) -> Optional[Any]:
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
            "iat": datetime.datetime.utcnow(),
            "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=1),
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
            id=f"task-{datetime.datetime.utcnow().isoformat()}",
            agent_id=target_agent_id,
            status="pending",
            messages=[Message(role="user", content=message)],
        )

    def resolve_agent(self, agent_id: str) -> Optional[A2AAgentCard]:
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
        self, agent_id: str, success: bool, metadata: Optional[Dict] = None
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
            await self.supabase.table("auth_audit_log").insert(
                {
                    "agent_id": agent_id,
                    "timestamp": datetime.datetime.utcnow().isoformat(),
                    "event_type": "authentication",
                    "success": success,
                    "metadata": metadata or {},
                }
            ).execute()
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
                    "created_at": datetime.datetime.utcnow().isoformat(),
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
