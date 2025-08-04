"""Phlow middleware - A2A Protocol extension with Supabase integration."""

import logging
import secrets
import string
import time
from collections.abc import Callable
from datetime import datetime, timedelta, timezone
from typing import Any

import httpx
import jwt
from a2a.client import A2AClient
from a2a.types import AgentCard as A2AAgentCard
from a2a.types import Task
from supabase import Client, create_client

from .circuit_breaker import (
    a2a_messaging_circuit_breaker,
    did_resolution_circuit_breaker,
    supabase_circuit_breaker,
)
from .distributed_rate_limiter import (
    create_rate_limiter_from_env,
)
from .exceptions import (
    AuthenticationError,
    CircuitBreakerError,
    ConfigurationError,
    RateLimitError,
)
from .monitoring import get_logger, get_metrics_collector
from .rbac import RoleCache, RoleCredentialVerifier
from .rbac.types import (
    RoleCredentialRequest,
    RoleCredentialResponse,
)
from .security import KeyManager, get_key_store
from .types import AgentCard, PhlowConfig, PhlowContext

# Use structured logger for better observability
structured_logger = get_logger()
metrics_collector = get_metrics_collector()

# Keep backwards compatibility
logger = logging.getLogger(__name__)


class PhlowMiddleware:
    """Phlow middleware for A2A Protocol with Supabase features."""

    def __init__(self, config: PhlowConfig):
        """Initialize Phlow middleware.

        Args:
            config: Phlow configuration
        """
        self.config = config
        self.supabase = create_client(config.supabase_url, config.supabase_anon_key)

        # Initialize key management
        self.key_store = get_key_store(config)
        self.key_manager = KeyManager(self.key_store)

        # Get keys from secure storage if not provided in config
        # Store as instance variables to avoid mutating the original config
        self.private_key = config.private_key
        self.public_key = config.public_key

        if not self.private_key or not self.public_key:
            agent_id = (config.agent_card.metadata or {}).get("agent_id", "default")
            stored_private, stored_public = self.key_manager.get_key_pair(agent_id)

            if not self.private_key and stored_private:
                self.private_key = stored_private
                logger.info(
                    f"Loaded private key from secure storage for agent {agent_id}"
                )

            if not self.public_key and stored_public:
                self.public_key = stored_public
                logger.info(
                    f"Loaded public key from secure storage for agent {agent_id}"
                )

        # Initialize A2A client with httpx client and agent card
        self.httpx_client = httpx.AsyncClient()
        self.a2a_client = A2AClient(
            httpx_client=self.httpx_client,
            agent_card=self._convert_to_a2a_agent_card(config.agent_card),
        )

        # Initialize RBAC components
        self.role_verifier = RoleCredentialVerifier(self.supabase)
        self.role_cache = RoleCache(self.supabase)

        # DID document cache for service endpoint resolution: {did: (document, expiry_timestamp)}
        self._did_document_cache: dict[str, tuple[dict, float]] = {}
        self._cache_ttl_seconds = 300  # 5 minutes cache
        self._max_cache_size = 1000  # Maximum number of cached DIDs

        # Rate limiters for different operations
        # Use distributed rate limiting if Redis is available
        rate_configs = config.rate_limit_configs
        self.auth_rate_limiter = create_rate_limiter_from_env(
            max_requests=rate_configs.auth_max_requests,
            window_ms=rate_configs.auth_window_ms,
        )
        self.role_request_rate_limiter = create_rate_limiter_from_env(
            max_requests=rate_configs.role_request_max_requests,
            window_ms=rate_configs.role_request_window_ms,
        )

        # Circuit breakers for external dependencies
        self.supabase_circuit_breaker = supabase_circuit_breaker()
        self.did_resolution_circuit_breaker = did_resolution_circuit_breaker()
        self.a2a_messaging_circuit_breaker = a2a_messaging_circuit_breaker()

        # Validate configuration
        if not config.supabase_url or not config.supabase_anon_key:
            raise ConfigurationError("Supabase URL and anon key are required")

    async def aclose(self) -> None:
        """Close all resources and cleanup."""
        try:
            if hasattr(self, "httpx_client") and self.httpx_client:
                await self.httpx_client.aclose()
        except Exception as e:
            logger.error(f"Error closing httpx client: {e}")

    async def __aenter__(self):
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.aclose()

    def _convert_to_a2a_agent_card(self, agent_card: AgentCard) -> A2AAgentCard:
        """Convert Phlow AgentCard to A2A AgentCard."""
        try:
            # Convert simple skills list to A2A format if needed
            a2a_skills = []
            for skill in agent_card.skills:
                if isinstance(skill, str):
                    # Convert string skill to A2A skill object
                    a2a_skills.append(
                        {
                            "name": skill,
                            "description": f"Skill: {skill}",
                        }
                    )
                else:
                    # Already in A2A format
                    a2a_skills.append(skill)

            return A2AAgentCard(
                name=agent_card.name,
                description=agent_card.description,
                url=agent_card.service_url,  # service_url -> url
                skills=a2a_skills,
                security_schemes=agent_card.security_schemes,
                capabilities={},  # Empty capabilities object
                version="1.0",  # Add required version field
                defaultInputModes=["text"],  # Default input modes
                defaultOutputModes=["text"],  # Default output modes
                # metadata is not a direct field in A2A AgentCard
            )
        except Exception as e:
            logger.error(f"Error converting AgentCard to A2A format: {e}")
            # Fallback to minimal A2A card
            return A2AAgentCard(
                name=agent_card.name,
                description=agent_card.description,
                url=agent_card.service_url,
                skills=[],
                capabilities={},
                version="1.0",
                defaultInputModes=["text"],
                defaultOutputModes=["text"],
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
        start_time = time.time()
        # Use cryptographically secure hash for token identification
        import hashlib

        token_hash = (
            hashlib.sha256(token[:50].encode() if token else b"unknown").hexdigest()[
                :16
            ]
            if token
            else "unknown"
        )
        agent_id = "unknown"

        try:
            # Input validation
            if not token or not isinstance(token, str):
                raise AuthenticationError("Token must be a non-empty string")

            if len(token) > 8192:  # Reasonable token size limit
                raise AuthenticationError("Token exceeds maximum length")

            # Basic JWT format validation (3 parts separated by dots)
            parts = token.split(".")
            if len(parts) != 3:
                raise AuthenticationError("Invalid token format")

            # Rate limiting based on token (to prevent token replay attacks)
            self.auth_rate_limiter.check_and_raise(token_hash)

            # Record rate limit check
            metrics_collector.record_rate_limit_check("auth", False)

            # Decode token with proper signature verification
            # Use correct key based on algorithm type
            if not self.private_key:
                raise AuthenticationError("No key configured for token verification")

            # Determine algorithm from token header but validate against allowed algorithms
            unverified_header = jwt.get_unverified_header(token)
            algorithm = unverified_header.get("alg", "HS256")

            # Define allowed algorithms and their required keys
            allowed_algorithms = {"HS256", "RS256"}
            if algorithm not in allowed_algorithms:
                raise AuthenticationError(
                    f"Algorithm {algorithm} not in allowed list: {allowed_algorithms}"
                )

            # Use appropriate key for verification based on algorithm
            if algorithm == "RS256":
                if not self.public_key:
                    raise AuthenticationError(
                        "Public key required for RS256 token verification"
                    )
                verification_key = self.public_key
            elif algorithm == "HS256":
                verification_key = self.private_key
            else:
                # This should never be reached due to the check above, but kept for safety
                raise AuthenticationError(f"Unsupported algorithm: {algorithm}")

            decoded = jwt.decode(
                token,
                verification_key,
                algorithms=[algorithm],
                options={"verify_signature": True, "require": ["exp", "iat"]},
            )

            # Extract agent ID for logging
            agent_id = decoded.get("sub", "unknown")

            # Set request context for logging
            structured_logger.set_request_context(ag_id=agent_id)

            # Create context with A2A integration
            context = PhlowContext(
                agent=self.config.agent_card,
                token=token,
                claims=decoded,
                supabase=self.supabase,
                a2a_client=self.a2a_client,
            )

            # Log successful authentication
            duration = time.time() - start_time
            structured_logger.log_authentication_event(
                agent_id=agent_id, success=True, token_hash=token_hash
            )
            metrics_collector.record_auth_attempt(agent_id, True, duration)

            return context

        except RateLimitError:
            # Rate limit exceeded
            metrics_collector.record_rate_limit_check("auth", True)
            structured_logger.log_authentication_event(
                agent_id=agent_id,
                success=False,
                token_hash=token_hash,
                error="rate_limit_exceeded",
            )
            raise
        except jwt.ExpiredSignatureError:
            error = AuthenticationError("Token has expired")
            self._log_auth_error(
                agent_id, token_hash, "token_expired", error, start_time
            )
            raise error
        except jwt.InvalidSignatureError:
            error = AuthenticationError("Invalid token signature")
            self._log_auth_error(
                agent_id, token_hash, "invalid_signature", error, start_time
            )
            raise error
        except jwt.DecodeError:
            error = AuthenticationError("Token is malformed and cannot be decoded")
            self._log_auth_error(
                agent_id, token_hash, "decode_error", error, start_time
            )
            raise error
        except jwt.InvalidKeyError:
            error = AuthenticationError("Invalid key for token verification")
            self._log_auth_error(agent_id, token_hash, "invalid_key", error, start_time)
            raise error
        except jwt.InvalidAlgorithmError:
            error = AuthenticationError("Invalid algorithm specified in token")
            self._log_auth_error(
                agent_id, token_hash, "invalid_algorithm", error, start_time
            )
            raise error
        except jwt.InvalidTokenError as e:
            # Catch any other JWT errors with specific message
            error_msg = str(e).lower()
            if "not enough segments" in error_msg:
                error = AuthenticationError(
                    "Token format is invalid (wrong number of segments)"
                )
                self._log_auth_error(
                    agent_id, token_hash, "invalid_format", error, start_time
                )
                raise error
            elif "invalid header" in error_msg:
                raise AuthenticationError("Token header is invalid")
            elif "invalid payload" in error_msg:
                raise AuthenticationError("Token payload is invalid")
            else:
                error = AuthenticationError(f"Token validation failed: {str(e)}")
                self._log_auth_error(
                    agent_id, token_hash, "validation_failed", error, start_time
                )
                raise error
        except Exception:
            # Catch any unexpected errors during token processing
            error = AuthenticationError(
                "Token verification failed due to internal error"
            )
            self._log_auth_error(
                agent_id, token_hash, "unexpected_error", error, start_time
            )
            raise error

    def _log_auth_error(
        self,
        agent_id: str,
        token_hash: str,
        error_type: str,
        error: Exception,
        start_time: float,
    ):
        """Log authentication error with metrics."""
        duration = time.time() - start_time
        structured_logger.log_authentication_event(
            agent_id=agent_id, success=False, token_hash=token_hash, error=error_type
        )
        metrics_collector.record_auth_attempt(agent_id, False, duration)

    async def authenticate_with_role(
        self, token: str, required_role: str
    ) -> PhlowContext:
        """Authenticate and verify role credentials.

        Args:
            token: JWT token
            required_role: The role string to verify (e.g., 'admin')

        Returns:
            PhlowContext with verified role information

        Raises:
            AuthenticationError: If authentication or role verification fails
        """
        # Input validation
        if not required_role or not isinstance(required_role, str):
            raise AuthenticationError("required_role must be a non-empty string")

        if len(required_role) > 100:  # Reasonable role name limit
            raise AuthenticationError("Role name exceeds maximum length")

        # Validate role format (alphanumeric, underscore, hyphen only)
        import re

        if not re.match(r"^[a-zA-Z0-9_-]+$", required_role):
            raise AuthenticationError("Role name contains invalid characters")
        # 1. Perform standard Phlow authentication first
        context = self.verify_token(token)

        # 2. Get agent ID from context
        agent_id = (
            context.agent.metadata.get("agent_id") if context.agent.metadata else None
        )
        if not agent_id:
            raise AuthenticationError("Agent ID not found in token")

        # Rate limiting for role requests by agent ID
        self.role_request_rate_limiter.check_and_raise(agent_id)

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
                nonce=nonce,
            )

            # Send A2A message to request role credential
            # Note: This is a simplified implementation
            # In practice, this would use the A2A client's messaging system
            role_response_data = await self._send_role_credential_request(
                agent_id, request_message
            )

            if not role_response_data:
                raise AuthenticationError(
                    f"No response received for role '{required_role}' request"
                )

            role_response = RoleCredentialResponse(**role_response_data)

            # 5. Verify the credential
            if role_response.presentation and not role_response.error:
                verification_result = await self.role_verifier.verify_presentation(
                    role_response.presentation, required_role
                )

                if verification_result.is_valid:
                    # 6. Cache the verified role
                    if verification_result.credential_hash:
                        await self.role_cache.cache_verified_role(
                            agent_id=agent_id,
                            role=required_role,
                            credential_hash=verification_result.credential_hash,
                            issuer_did=verification_result.issuer_did,
                            expires_at=verification_result.expires_at,
                        )

                    context.verified_roles = [required_role]
                    return context
                else:
                    raise AuthenticationError(
                        f"Role credential verification failed: {verification_result.error_message}"
                    )
            else:
                error_msg = role_response.error or "No valid presentation provided"
                raise AuthenticationError(
                    f"Role credential request failed: {error_msg}"
                )

        except Exception as e:
            if isinstance(e, AuthenticationError):
                raise
            raise AuthenticationError(f"Error during role verification: {str(e)}")

    async def _send_role_credential_request(
        self, agent_id: str, request: RoleCredentialRequest
    ) -> dict | None:
        """Send role credential request via A2A messaging.

        Implements proper A2A Protocol messaging with:
        1. Agent endpoint resolution via agent registry or DID
        2. HTTP POST to /tasks/send endpoint with proper A2A Task format
        3. Authentication headers and timeout handling
        4. Comprehensive error handling and retries

        Args:
            agent_id: Target agent ID
            request: Role credential request

        Returns:
            Response data or None if failed
        """
        try:
            # 1. Resolve target agent's service endpoint
            agent_endpoint = await self._resolve_agent_endpoint(agent_id)
            if not agent_endpoint:
                logger.error(f"Could not resolve endpoint for agent {agent_id}")
                return None

            # 2. Create A2A Task message
            task_message = {
                "type": "task",
                "id": f"role-request-{self._generate_nonce()}",
                "description": f"Request role credential for '{request.required_role}'",
                "parameters": {
                    "message_type": request.type,
                    "required_role": request.required_role,
                    "context": request.context,
                    "nonce": request.nonce,
                },
                "requirements": {
                    "output_schema": {
                        "type": "object",
                        "properties": {
                            "type": {
                                "type": "string",
                                "const": "role-credential-response",
                            },
                            "nonce": {"type": "string"},
                            "presentation": {"type": "object"},
                            "error": {"type": "string"},
                        },
                        "required": ["type", "nonce"],
                    }
                },
            }

            # 3. Send HTTP POST to agent's /tasks/send endpoint
            headers = {
                "Content-Type": "application/json",
                "User-Agent": f"Phlow/{self.config.agent_card.name}",
                "Authorization": f"Bearer {self._generate_auth_token_for_agent(agent_id)}",
            }

            tasks_endpoint = f"{agent_endpoint.rstrip('/')}/tasks/send"

            async with httpx.AsyncClient(timeout=30.0) as client:
                logger.info(f"Sending role credential request to {tasks_endpoint}")

                response = await client.post(
                    tasks_endpoint, json=task_message, headers=headers
                )

                response.raise_for_status()
                response_data = response.json()

            # 4. Parse A2A Task response
            if response_data.get("status") == "completed":
                # Extract role credential response from task result
                task_result = response_data.get("result", {})
                if (
                    isinstance(task_result, dict)
                    and task_result.get("type") == "role-credential-response"
                ):
                    return task_result
                else:
                    logger.error(f"Invalid task result format: {task_result}")
                    return None
            elif response_data.get("status") == "failed":
                error_msg = response_data.get("error", "Task failed")
                logger.error(f"A2A task failed: {error_msg}")
                return {
                    "type": "role-credential-response",
                    "nonce": request.nonce,
                    "error": error_msg,
                }
            else:
                # Handle async task case - would need polling in production
                logger.warning(
                    f"A2A task is async (status: {response_data.get('status')}), polling not implemented"
                )
                return {
                    "type": "role-credential-response",
                    "nonce": request.nonce,
                    "error": "Async task responses not supported yet",
                }

        except httpx.TimeoutException:
            logger.error(f"Timeout waiting for response from agent {agent_id}")
            return None
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error from agent {agent_id}: {e.response.status_code}")
            return None
        except Exception as e:
            logger.error(f"Error sending role credential request to {agent_id}: {e}")
            return None

    async def _resolve_agent_endpoint(self, agent_id: str) -> str | None:
        """Resolve agent service endpoint from registry or DID document.

        Args:
            agent_id: Agent ID to resolve

        Returns:
            Service endpoint URL or None if not found
        """
        try:
            # 1. First try to resolve from Supabase agent registry
            result = (
                self.supabase.table("agent_cards")
                .select("service_url")
                .eq("agent_id", agent_id)
                .single()
                .execute()
            )

            if result.data and result.data.get("service_url"):
                return result.data["service_url"]

            # 2. If agent_id is a DID, try DID document resolution
            if agent_id.startswith("did:"):
                return await self._resolve_did_service_endpoint(agent_id)

            # 3. Fallback: check if agent_id is already a URL
            if agent_id.startswith(("http://", "https://")):
                return agent_id

            logger.warning(f"Could not resolve endpoint for agent {agent_id}")
            return None

        except Exception as e:
            logger.error(f"Error resolving agent endpoint for {agent_id}: {e}")
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
        """Cache a DID document with expiration and bounded size.

        Args:
            did: DID identifier
            document: DID document to cache
        """
        import time

        # Clean up expired entries first
        self._cleanup_did_cache()

        # Enforce cache size limit using LRU eviction
        if len(self._did_document_cache) >= self._max_cache_size:
            # Remove 20% of oldest entries to make room
            sorted_entries = sorted(
                self._did_document_cache.items(),
                key=lambda x: x[1][1],  # Sort by expiry timestamp
            )

            num_to_remove = max(
                1, self._max_cache_size // 5
            )  # Remove at least 1, up to 20%
            for did_to_remove, _ in sorted_entries[:num_to_remove]:
                del self._did_document_cache[did_to_remove]

        expiry = time.time() + self._cache_ttl_seconds
        self._did_document_cache[did] = (document, expiry)

    def _cleanup_did_cache(self) -> None:
        """Clean up expired DID document cache entries with error handling."""
        import time

        now = time.time()

        # Process in batches to avoid memory issues and handle errors gracefully
        items_to_remove = []
        try:
            # Collect expired items in batches
            for did, (_, expiry) in list(self._did_document_cache.items()):
                if expiry <= now:
                    items_to_remove.append(did)

                # Process in batches of 100 to avoid memory issues
                if len(items_to_remove) >= 100:
                    self._remove_cache_items(items_to_remove)
                    items_to_remove = []

            # Process remaining items
            if items_to_remove:
                self._remove_cache_items(items_to_remove)

        except Exception as e:
            logger.error(f"Error during DID cache cleanup: {e}")
            # Continue with partial cleanup rather than failing completely

    def _remove_cache_items(self, items_to_remove: list[str]) -> None:
        """Safely remove items from cache with individual error handling."""
        for did in items_to_remove:
            try:
                if did in self._did_document_cache:
                    del self._did_document_cache[did]
            except Exception as e:
                logger.warning(f"Failed to remove DID {did} from cache: {e}")
                # Continue removing other items

    async def _resolve_did_service_endpoint(self, did: str) -> str | None:
        """Resolve service endpoint from DID document with caching.

        Args:
            did: DID identifier

        Returns:
            Service endpoint URL or None if not found
        """
        try:
            # Check cache first
            did_doc = self._get_cached_did_document(did)
            cached = did_doc is not None

            if not did_doc:
                # Cache miss - fetch DID document with circuit breaker protection
                if did.startswith("did:web:"):
                    domain = did.replace("did:web:", "")
                    did_doc_url = f"https://{domain}/.well-known/did.json"

                    # Use circuit breaker for external HTTP calls
                    async def fetch_did_document():
                        async with httpx.AsyncClient(timeout=10.0) as client:
                            response = await client.get(did_doc_url)
                            response.raise_for_status()
                            return response.json()

                    did_doc = await self.did_resolution_circuit_breaker.acall(
                        fetch_did_document
                    )

                    # Cache the document
                    self._cache_did_document(did, did_doc)

                    # Log successful DID resolution
                    structured_logger.log_did_resolution_event(
                        did=did, success=True, cached=False
                    )
                else:
                    logger.warning(
                        f"Unsupported DID method for service endpoint resolution: {did}"
                    )
                    return None

            # Look for service endpoints in cached/fetched document
            services = did_doc.get("service", [])
            for service in services:
                if service.get("type") in [
                    "A2AService",
                    "PhLowService",
                    "AgentService",
                ]:
                    endpoint = service.get("serviceEndpoint")
                    if cached:
                        structured_logger.log_did_resolution_event(
                            did=did, success=True, cached=True
                        )
                    return endpoint

        except CircuitBreakerError as e:
            # Circuit breaker is open
            structured_logger.log_did_resolution_event(
                did=did, success=False, cached=False, error="circuit_breaker_open"
            )
            logger.error(f"DID resolution circuit breaker open for {did}: {e}")
        except Exception as e:
            # Other errors
            structured_logger.log_did_resolution_event(
                did=did, success=False, cached=cached, error=str(e)
            )
            logger.error(f"Error resolving DID service endpoint for {did}: {e}")

        return None

    def _generate_auth_token_for_agent(self, target_agent_id: str) -> str:
        """Generate authentication token for A2A communication.

        Args:
            target_agent_id: Target agent ID

        Returns:
            JWT token for authentication
        """
        payload = {
            "sub": self.config.agent_card.metadata.get("agent_id")
            if self.config.agent_card.metadata
            else None,
            "aud": target_agent_id,
            "iss": self.config.agent_card.name,
            "iat": datetime.now(timezone.utc),
            "exp": datetime.now(timezone.utc)
            + timedelta(minutes=5),  # Short-lived token
            "purpose": "role-credential-request",
        }

        token = jwt.encode(payload, self.private_key, algorithm="HS256")
        return token

    def _generate_nonce(self) -> str:
        """Generate a random nonce for role credential requests.

        Returns:
            Random alphanumeric string
        """
        return "".join(
            secrets.choice(string.ascii_letters + string.digits) for _ in range(16)
        )

    def get_a2a_client(self) -> Any | None:
        """Get the A2A client instance."""
        return self.a2a_client

    def get_supabase_client(self) -> Client:
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

        token = jwt.encode(payload, self.private_key, algorithm="HS256")
        return token

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

    async def log_agent_heartbeat(self, agent_id: str) -> None:
        """Update agent heartbeat timestamp and status.

        Args:
            agent_id: Agent ID to update
        """
        if not self.config.enable_audit_log:
            return

        try:
            await (
                self.supabase.table("agent_cards")
                .update({"last_heartbeat": "now()", "status": "IDLE"})
                .eq("agent_id", agent_id)
                .execute()
            )

            structured_logger.log_event(
                "agent_heartbeat",
                agent_id=agent_id,
                timestamp=datetime.now(timezone.utc).isoformat(),
            )

        except Exception as e:
            structured_logger.log_event(
                "agent_heartbeat_failed", agent_id=agent_id, error=str(e)
            )

    async def log_task_received(
        self, task_id: str, agent_id: str, client_agent_id: str, task_type: str
    ) -> None:
        """Log when a task is received and update agent status.

        Args:
            task_id: Unique task identifier
            agent_id: Agent receiving the task
            client_agent_id: Agent requesting the task
            task_type: Type/category of the task
        """
        if not self.config.enable_audit_log:
            return

        try:
            # Insert task record
            await (
                self.supabase.table("phlow_tasks")
                .insert(
                    {
                        "task_id": task_id,
                        "agent_id": agent_id,
                        "client_agent_id": client_agent_id,
                        "task_type": task_type,
                        "status": "SUBMITTED",
                    }
                )
                .execute()
            )

            # Update agent status and increment active tasks
            await (
                self.supabase.table("agent_cards")
                .update({"status": "WORKING", "last_heartbeat": "now()"})
                .eq("agent_id", agent_id)
                .execute()
            )

            # Increment active tasks count using RPC function
            await self.supabase.rpc(
                "increment_active_tasks", {"p_agent_id": agent_id}
            ).execute()

            structured_logger.log_event(
                "task_received",
                task_id=task_id,
                agent_id=agent_id,
                client_agent_id=client_agent_id,
                task_type=task_type,
            )

            metrics_collector.increment_counter(
                "phlow_tasks_received_total",
                labels={"agent_id": agent_id, "task_type": task_type},
            )

        except Exception as e:
            structured_logger.log_event(
                "task_received_failed", task_id=task_id, agent_id=agent_id, error=str(e)
            )

    async def log_task_status(
        self, task_id: str, status: str, error_message: str | None = None
    ) -> None:
        """Update task status and handle agent active task count.

        Args:
            task_id: Task identifier
            status: New status (SUBMITTED, WORKING, COMPLETED, FAILED)
            error_message: Optional error message for failed tasks
        """
        if not self.config.enable_audit_log:
            return

        try:
            # Prepare update data
            update_data = {"status": status, "updated_at": "now()"}
            if error_message:
                update_data["error_message"] = error_message

            # Update task status
            await (
                self.supabase.table("phlow_tasks")
                .update(update_data)
                .eq("task_id", task_id)
                .execute()
            )

            # If task is completed or failed, decrement active tasks
            if status in ["COMPLETED", "FAILED"]:
                # Get the agent_id for this task
                task_result = await (
                    self.supabase.table("phlow_tasks")
                    .select("agent_id")
                    .eq("task_id", task_id)
                    .single()
                    .execute()
                )

                if task_result.data:
                    agent_id = task_result.data["agent_id"]

                    # Decrement active tasks count
                    await self.supabase.rpc(
                        "decrement_active_tasks", {"p_agent_id": agent_id}
                    ).execute()

                    # Update agent status to IDLE if no more active tasks
                    active_tasks_result = await (
                        self.supabase.table("agent_cards")
                        .select("active_tasks")
                        .eq("agent_id", agent_id)
                        .single()
                        .execute()
                    )

                    if (
                        active_tasks_result.data
                        and active_tasks_result.data.get("active_tasks", 0) <= 0
                    ):
                        await (
                            self.supabase.table("agent_cards")
                            .update({"status": "IDLE"})
                            .eq("agent_id", agent_id)
                            .execute()
                        )

            structured_logger.log_event(
                "task_status_updated",
                task_id=task_id,
                status=status,
                error_message=error_message,
            )

            metrics_collector.increment_counter(
                "phlow_task_status_changes_total", labels={"status": status}
            )

        except Exception as e:
            structured_logger.log_event(
                "task_status_update_failed",
                task_id=task_id,
                status=status,
                error=str(e),
            )

    async def log_message(
        self,
        task_id: str,
        source_agent_id: str,
        target_agent_id: str,
        message_type: str,
        content: dict,
    ) -> None:
        """Log inter-agent message for task communication tracking.

        Args:
            task_id: Task identifier
            source_agent_id: Agent sending the message
            target_agent_id: Agent receiving the message
            message_type: Type of message (request, response, error)
            content: Message content/payload
        """
        if not self.config.enable_audit_log:
            return

        try:
            await (
                self.supabase.table("phlow_messages")
                .insert(
                    {
                        "task_id": task_id,
                        "source_agent_id": source_agent_id,
                        "target_agent_id": target_agent_id,
                        "message_type": message_type,
                        "content": content,
                    }
                )
                .execute()
            )

            structured_logger.log_event(
                "message_logged",
                task_id=task_id,
                source_agent_id=source_agent_id,
                target_agent_id=target_agent_id,
                message_type=message_type,
            )

            metrics_collector.increment_counter(
                "phlow_messages_total",
                labels={
                    "source_agent": source_agent_id,
                    "target_agent": target_agent_id,
                    "message_type": message_type,
                },
            )

        except Exception as e:
            structured_logger.log_event(
                "message_logging_failed",
                task_id=task_id,
                source_agent_id=source_agent_id,
                target_agent_id=target_agent_id,
                error=str(e),
            )

    async def log_auth_event(
        self, agent_id: str, success: bool, metadata: dict | None = None
    ) -> None:
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

    def authenticate(self) -> Callable[[Any], Any]:
        """Return authentication middleware function.

        For use with web frameworks like FastAPI or Flask.
        This would need framework-specific implementation.
        """

        def middleware(request: Any) -> Any:
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
