"""Phlow middleware - A2A Protocol extension with Supabase integration."""

from typing import Any, Dict, Optional
from a2a_sdk import A2AServer, A2AContext, AgentCard as A2AAgentCard
from supabase import Client, create_client

from .audit import AuditLogger, create_audit_entry
from .exceptions import ConfigurationError, RateLimitError
from .rate_limiter import RateLimiter
from .types import PhlowConfig, PhlowContext


class PhlowMiddleware(A2AServer):
    """Phlow middleware extending A2A Protocol with Supabase features."""

    def __init__(self, config: PhlowConfig):
        """Initialize Phlow middleware.

        Args:
            config: Phlow configuration

        Raises:
            ConfigurationError: If configuration is invalid
        """
        # Initialize A2A server with agent card
        super().__init__(
            agent_card=config.agent_card,
            private_key=config.private_key,
            # A2A SDK handles JWT validation internally
        )

        self._validate_config(config)
        self.config = config

        # Initialize Supabase client
        self.supabase: Client = create_client(
            config.supabase_url, config.supabase_anon_key
        )

        # Initialize rate limiter if configured
        self.rate_limiter: Optional[RateLimiter] = None
        if config.rate_limiting:
            self.rate_limiter = RateLimiter(
                config.rate_limiting["max_requests"], 
                config.rate_limiting["window_ms"]
            )

        # Initialize audit logger if enabled
        self.audit_logger: Optional[AuditLogger] = None
        if config.enable_audit:
            self.audit_logger = AuditLogger(self.supabase)

        # Set up Supabase integration hooks
        self._setup_supabase_hooks()

    def _validate_config(self, config: PhlowConfig) -> None:
        """Validate configuration.

        Args:
            config: Configuration to validate

        Raises:
            ConfigurationError: If configuration is invalid
        """
        if not config.supabase_url or not config.supabase_anon_key:
            raise ConfigurationError("Supabase URL and anon key are required")

    def _setup_supabase_hooks(self) -> None:
        """Set up hooks for Supabase integration."""
        # Override A2A's authentication hook
        self.on_authenticated = self._on_authenticated
        
        # Override agent lookup to use Supabase
        self.on_agent_lookup = self._get_agent_from_supabase

    async def _on_authenticated(self, context: A2AContext) -> None:
        """Handle successful authentication.

        Args:
            context: A2A authentication context
        """
        agent_id = context.agent.metadata.get("agentId", "unknown")
        
        # Check rate limiting
        if self.rate_limiter and not self.rate_limiter.is_allowed(agent_id):
            await self._log_audit(
                "auth_failure", agent_id, details={"reason": "rate_limit"}
            )
            raise RateLimitError("Rate limit exceeded")

        # Log successful authentication
        if self.audit_logger:
            await self._log_audit(
                "auth_success", 
                agent_id, 
                self.config.agent_card.metadata.get("agentId")
            )

        # Attach Supabase client to context
        context.extensions = context.extensions or {}
        context.extensions["supabase"] = self.supabase

    async def _get_agent_from_supabase(self, agent_id: str) -> Optional[A2AAgentCard]:
        """Get agent card from Supabase.

        Args:
            agent_id: Agent ID to look up

        Returns:
            A2A-compliant agent card or None if not found
        """
        try:
            result = (
                self.supabase.table("agent_cards")
                .select("*")
                .eq("agent_id", agent_id)
                .single()
                .execute()
            )

            if not result.data:
                return None

            data = result.data
            
            # Return A2A-compliant agent card
            return A2AAgentCard(
                schema_version=data.get("schema_version", "1.0"),
                name=data["name"],
                description=data.get("description"),
                service_url=data.get("service_url"),
                skills=data.get("skills", []),
                security_schemes=data.get("security_schemes", {}),
                metadata={
                    **data.get("metadata", {}),
                    "agentId": data["agent_id"],
                    "publicKey": data["public_key"],
                }
            )

        except Exception:
            return None

    async def authenticate_with_context(
        self, token: str, agent_id: str
    ) -> PhlowContext:
        """Authenticate and return Phlow context.

        This method provides backward compatibility with existing Phlow code.

        Args:
            token: JWT token to verify
            agent_id: Agent ID from request headers

        Returns:
            Phlow-specific authentication context
        """
        # Use A2A's authentication
        a2a_context = await self.authenticate(token, agent_id)
        
        # Create Phlow context from A2A context
        return PhlowContext(
            agent=a2a_context.agent,
            token=a2a_context.token,
            claims=a2a_context.claims,
            supabase=self.supabase,
        )

    async def _log_audit(
        self,
        event: str,
        agent_id: str,
        target_agent_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Log an audit event.

        Args:
            event: Event type
            agent_id: Agent that triggered the event
            target_agent_id: Target agent (optional)
            details: Additional details (optional)
        """
        if not self.audit_logger:
            return

        entry = create_audit_entry(event, agent_id, target_agent_id, details)
        await self.audit_logger.log(entry)

    def get_supabase_client(self) -> Client:
        """Get the Supabase client.

        Returns:
            Supabase client instance
        """
        return self.supabase

    def generate_rls_policy(self, agent_id: str, permissions: list[str]) -> str:
        """Generate Row Level Security policy for Supabase.

        Args:
            agent_id: Agent ID for the policy
            permissions: List of required permissions

        Returns:
            SQL policy statement
        """
        permission_checks = " OR ".join(
            f"auth.jwt() ->> 'permissions' ? '{p}'" for p in permissions
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

    async def register_agent(self, agent_card: A2AAgentCard) -> None:
        """Register an agent in Supabase.

        Args:
            agent_card: A2A-compliant agent card to register
        """
        agent_id = agent_card.metadata.get("agentId")
        if not agent_id:
            raise ValueError("Agent ID is required in metadata")

        data = {
            "agent_id": agent_id,
            "name": agent_card.name,
            "description": agent_card.description,
            "service_url": agent_card.service_url,
            "schema_version": agent_card.schema_version,
            "skills": agent_card.skills,
            "security_schemes": agent_card.security_schemes,
            "public_key": agent_card.metadata.get("publicKey"),
            "metadata": agent_card.metadata,
            "created_at": "now()",
        }

        result = self.supabase.table("agent_cards").upsert(data).execute()
        
        if result.error:
            raise Exception(f"Failed to register agent: {result.error.message}")