"""Core middleware for Phlow authentication."""

import asyncio
from typing import Any, Dict, Optional

from supabase import Client, create_client

from .audit import AuditLogger, create_audit_entry
from .exceptions import (
    AuthenticationError,
    AuthorizationError,
    ConfigurationError,
    RateLimitError,
)
from .jwt_utils import decode_token, is_token_expired, verify_token
from .rate_limiter import RateLimiter
from .types import AgentCard, PhlowConfig, PhlowContext, VerifyOptions


class PhlowMiddleware:
    """Core Phlow authentication middleware."""

    def __init__(self, config: PhlowConfig):
        """Initialize Phlow middleware.

        Args:
            config: Phlow configuration

        Raises:
            ConfigurationError: If configuration is invalid
        """
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
                config.rate_limiting["max_requests"], config.rate_limiting["window_ms"]
            )

        # Initialize audit logger if enabled
        self.audit_logger: Optional[AuditLogger] = None
        if config.enable_audit:
            self.audit_logger = AuditLogger(self.supabase)

    def _validate_config(self, config: PhlowConfig) -> None:
        """Validate configuration.

        Args:
            config: Configuration to validate

        Raises:
            ConfigurationError: If configuration is invalid
        """
        if not config.supabase_url or not config.supabase_anon_key:
            raise ConfigurationError("Supabase URL and anon key are required")

        if not config.agent_card or not config.agent_card.agent_id:
            raise ConfigurationError("Agent card with agent_id is required")

        if not config.private_key:
            raise ConfigurationError("Private key is required")

    async def authenticate(
        self, token: str, agent_id: str, options: Optional[VerifyOptions] = None
    ) -> PhlowContext:
        """Authenticate a request.

        Args:
            token: JWT token to verify
            agent_id: Agent ID from request headers
            options: Verification options

        Returns:
            Authentication context

        Raises:
            AuthenticationError: If authentication fails
            AuthorizationError: If authorization fails
            RateLimitError: If rate limit is exceeded
        """
        if options is None:
            options = VerifyOptions()

        # Check rate limiting
        if self.rate_limiter and not self.rate_limiter.is_allowed(agent_id):
            await self._log_audit(
                "auth_failure", agent_id, details={"reason": "rate_limit"}
            )
            raise RateLimitError("Rate limit exceeded")

        # Get agent card from database
        agent_card = await self._get_agent_card(agent_id)
        if not agent_card:
            await self._log_audit(
                "auth_failure", agent_id, details={"reason": "agent_not_found"}
            )
            raise AuthenticationError("Agent not found", "AGENT_NOT_FOUND")

        # Verify token
        try:
            claims = verify_token(
                token,
                agent_card.public_key,
                audience=self.config.agent_card.agent_id,
                issuer=agent_id,
                ignore_expiration=options.allow_expired,
            )
        except Exception as e:
            await self._log_audit("auth_failure", agent_id, details={"reason": str(e)})
            raise

        # Check permissions
        if options.required_permissions:
            missing_permissions = set(options.required_permissions) - set(
                claims.permissions
            )
            if missing_permissions:
                await self._log_audit(
                    "permission_denied",
                    agent_id,
                    self.config.agent_card.agent_id,
                    details={
                        "required": options.required_permissions,
                        "provided": claims.permissions,
                        "missing": list(missing_permissions),
                    },
                )
                raise AuthorizationError(
                    "Insufficient permissions", "INSUFFICIENT_PERMISSIONS"
                )

        # Log successful authentication
        await self._log_audit("auth_success", agent_id, self.config.agent_card.agent_id)

        # Create context
        context = PhlowContext(
            agent=agent_card,
            token=token,
            claims=claims,
            supabase=self.supabase,
        )

        return context

    def authenticate_sync(
        self, token: str, agent_id: str, options: Optional[VerifyOptions] = None
    ) -> PhlowContext:
        """Synchronous version of authenticate.

        Args:
            token: JWT token to verify
            agent_id: Agent ID from request headers
            options: Verification options

        Returns:
            Authentication context
        """
        # Create event loop if none exists
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        return loop.run_until_complete(self.authenticate(token, agent_id, options))

    async def check_token_refresh(self, token: str) -> bool:
        """Check if token needs refreshing.

        Args:
            token: JWT token to check

        Returns:
            True if token should be refreshed
        """
        threshold = self.config.refresh_threshold
        needs_refresh = is_token_expired(token, threshold)

        if needs_refresh:
            # Log token refresh event
            decoded = decode_token(token)
            if decoded:
                await self._log_audit(
                    "token_refresh", decoded.iss, self.config.agent_card.agent_id
                )

        return needs_refresh

    async def _get_agent_card(self, agent_id: str) -> Optional[AgentCard]:
        """Get agent card from database.

        Args:
            agent_id: Agent ID to look up

        Returns:
            Agent card or None if not found
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
            return AgentCard(
                agent_id=data["agent_id"],
                name=data["name"],
                description=data.get("description"),
                permissions=data.get("permissions", []),
                public_key=data["public_key"],
                endpoints=data.get("endpoints"),
                metadata=data.get("metadata"),
            )

        except Exception:
            return None

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

    def get_agent_card(self) -> AgentCard:
        """Get the current agent card.

        Returns:
            Current agent card
        """
        return self.config.agent_card
