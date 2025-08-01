"""Role verification caching using Supabase."""

import logging
from datetime import datetime, timezone

from supabase import Client

from .types import CachedRole

logger = logging.getLogger(__name__)


class RoleCache:
    """Manages caching of verified role credentials in Supabase."""

    def __init__(self, supabase_client: Client):
        """Initialize cache with Supabase client.

        Args:
            supabase_client: Supabase client for database operations
        """
        self.supabase = supabase_client
        self.table_name = "verified_roles"

    async def get_cached_role(
        self,
        agent_id: str,
        role: str
    ) -> CachedRole | None:
        """Retrieve a cached role verification.

        Args:
            agent_id: ID of the agent
            role: Role to check

        Returns:
            Cached role data if found and valid, None otherwise
        """
        try:
            result = self.supabase.table(self.table_name).select("*").eq(
                "agent_id", agent_id
            ).eq("role", role).execute()

            if not result.data:
                return None

            cached_data = result.data[0]
            cached_role = CachedRole(
                id=cached_data["id"],
                agent_id=cached_data["agent_id"],
                role=cached_data["role"],
                verified_at=datetime.fromisoformat(cached_data["verified_at"]),
                expires_at=(
                    datetime.fromisoformat(cached_data["expires_at"])
                    if cached_data["expires_at"]
                    else None
                ),
                credential_hash=cached_data["credential_hash"],
                issuer_did=cached_data.get("issuer_did"),
                metadata=cached_data.get("metadata", {})
            )

            # Check if cached role has expired
            if self.is_expired(cached_role):
                await self.remove_cached_role(agent_id, role)
                return None

            return cached_role

        except Exception as e:
            logger.error(f"Error retrieving cached role: {e}")
            return None

    async def cache_verified_role(
        self,
        agent_id: str,
        role: str,
        credential_hash: str,
        issuer_did: str | None = None,
        expires_at: datetime | None = None,
        metadata: dict | None = None
    ) -> bool:
        """Cache a verified role credential.

        Args:
            agent_id: ID of the agent
            role: The verified role
            credential_hash: Hash of the credential
            issuer_did: DID of the credential issuer
            expires_at: When the credential expires
            metadata: Additional metadata

        Returns:
            True if successfully cached
        """
        try:
            data = {
                "agent_id": agent_id,
                "role": role,
                "verified_at": datetime.now(timezone.utc).isoformat(),
                "credential_hash": credential_hash,
                "issuer_did": issuer_did,
                "expires_at": expires_at.isoformat() if expires_at else None,
                "metadata": metadata or {}
            }

            result = self.supabase.table(self.table_name).upsert(data).execute()

            if result.data:
                logger.info(f"Cached role '{role}' for agent '{agent_id}'")
                return True
            else:
                logger.error(f"Failed to cache role: {result}")
                return False

        except Exception as e:
            logger.error(f"Error caching verified role: {e}")
            return False

    async def remove_cached_role(self, agent_id: str, role: str) -> bool:
        """Remove a cached role verification.

        Args:
            agent_id: ID of the agent
            role: Role to remove

        Returns:
            True if successfully removed
        """
        try:
            self.supabase.table(self.table_name).delete().eq(
                "agent_id", agent_id
            ).eq("role", role).execute()

            logger.info(f"Removed cached role '{role}' for agent '{agent_id}'")
            return True

        except Exception as e:
            logger.error(f"Error removing cached role: {e}")
            return False

    async def get_agent_roles(self, agent_id: str) -> list[CachedRole]:
        """Get all cached roles for an agent.

        Args:
            agent_id: ID of the agent

        Returns:
            List of cached roles
        """
        try:
            result = self.supabase.table(self.table_name).select("*").eq(
                "agent_id", agent_id
            ).execute()

            roles = []
            for data in result.data:
                cached_role = CachedRole(
                    id=data["id"],
                    agent_id=data["agent_id"],
                    role=data["role"],
                    verified_at=datetime.fromisoformat(data["verified_at"]),
                    expires_at=(
                        datetime.fromisoformat(data["expires_at"])
                        if data["expires_at"]
                        else None
                    ),
                    credential_hash=data["credential_hash"],
                    issuer_did=data.get("issuer_did"),
                    metadata=data.get("metadata", {})
                )

                # Only return non-expired roles
                if not self.is_expired(cached_role):
                    roles.append(cached_role)
                else:
                    # Clean up expired role
                    await self.remove_cached_role(agent_id, cached_role.role)

            return roles

        except Exception as e:
            logger.error(f"Error retrieving agent roles: {e}")
            return []

    async def cleanup_expired_roles(self) -> int:
        """Clean up expired role verifications.

        Returns:
            Number of expired roles removed
        """
        try:
            now = datetime.now(timezone.utc).isoformat()

            # Find expired roles
            result = self.supabase.table(self.table_name).select("id").lt(
                "expires_at", now
            ).is_("expires_at", "not.null").execute()

            if not result.data:
                return 0

            # Delete expired roles
            expired_ids = [row["id"] for row in result.data]
            self.supabase.table(self.table_name).delete().in_(
                "id", expired_ids
            ).execute()

            count = len(expired_ids)
            logger.info(f"Cleaned up {count} expired role verifications")
            return count

        except Exception as e:
            logger.error(f"Error cleaning up expired roles: {e}")
            return 0

    def is_expired(self, cached_role: CachedRole) -> bool:
        """Check if a cached role has expired.

        Args:
            cached_role: The cached role to check

        Returns:
            True if expired
        """
        if not cached_role.expires_at:
            return False

        return cached_role.expires_at < datetime.now(timezone.utc)
