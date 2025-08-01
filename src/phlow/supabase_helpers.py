"""Supabase helper utilities for Phlow authentication."""

from datetime import datetime
from typing import Any, Dict, List, Optional

from supabase import Client

from .types import AgentCard


class SupabaseHelpers:
    """Helper class for Supabase operations."""

    def __init__(self, supabase_client: Client):
        """Initialize Supabase helpers.

        Args:
            supabase_client: Supabase client instance
        """
        self.supabase = supabase_client

    async def register_agent_card(self, agent_card: AgentCard) -> None:
        """Register an agent card in the database.

        Args:
            agent_card: Agent card to register

        Raises:
            Exception: If registration fails
        """
        data = {
            "agent_id": agent_card.agent_id,
            "name": agent_card.name,
            "description": agent_card.description,
            "permissions": agent_card.permissions,
            "public_key": agent_card.public_key,
            "endpoints": agent_card.endpoints or {},
            "metadata": agent_card.metadata or {},
            "updated_at": datetime.utcnow().isoformat(),
        }

        result = self.supabase.table("agent_cards").upsert(data).execute()

        if result.data is None:
            raise Exception(f"Failed to register agent card: {result}")

    def register_agent_card_sync(self, agent_card: AgentCard) -> None:
        """Synchronously register an agent card.

        Args:
            agent_card: Agent card to register
        """
        data = {
            "agent_id": agent_card.agent_id,
            "name": agent_card.name,
            "description": agent_card.description,
            "permissions": agent_card.permissions,
            "public_key": agent_card.public_key,
            "endpoints": agent_card.endpoints or {},
            "metadata": agent_card.metadata or {},
            "updated_at": datetime.utcnow().isoformat(),
        }

        result = self.supabase.table("agent_cards").upsert(data).execute()

        if result.data is None:
            raise Exception(f"Failed to register agent card: {result}")

    async def get_agent_card(self, agent_id: str) -> Optional[AgentCard]:
        """Get an agent card from the database.

        Args:
            agent_id: Agent ID to look up

        Returns:
            Agent card or None if not found
        """
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

    def get_agent_card_sync(self, agent_id: str) -> Optional[AgentCard]:
        """Synchronously get an agent card.

        Args:
            agent_id: Agent ID to look up

        Returns:
            Agent card or None if not found
        """
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

    async def list_agent_cards(
        self,
        permissions: Optional[List[str]] = None,
        metadata_filters: Optional[Dict[str, Any]] = None,
    ) -> List[AgentCard]:
        """List agent cards with optional filtering.

        Args:
            permissions: Filter by required permissions
            metadata_filters: Filter by metadata fields

        Returns:
            List of matching agent cards
        """
        query = self.supabase.table("agent_cards").select("*")

        # Apply permission filters
        if permissions:
            for permission in permissions:
                query = query.contains("permissions", [permission])

        # Apply metadata filters
        if metadata_filters:
            for key, value in metadata_filters.items():
                query = query.eq(f"metadata->>{key}", value)

        result = query.execute()

        if not result.data:
            return []

        agent_cards = []
        for data in result.data:
            agent_card = AgentCard(
                agent_id=data["agent_id"],
                name=data["name"],
                description=data.get("description"),
                permissions=data.get("permissions", []),
                public_key=data["public_key"],
                endpoints=data.get("endpoints"),
                metadata=data.get("metadata"),
            )
            agent_cards.append(agent_card)

        return agent_cards

    def list_agent_cards_sync(
        self,
        permissions: Optional[List[str]] = None,
        metadata_filters: Optional[Dict[str, Any]] = None,
    ) -> List[AgentCard]:
        """Synchronously list agent cards.

        Args:
            permissions: Filter by required permissions
            metadata_filters: Filter by metadata fields

        Returns:
            List of matching agent cards
        """
        query = self.supabase.table("agent_cards").select("*")

        # Apply permission filters
        if permissions:
            for permission in permissions:
                query = query.contains("permissions", [permission])

        # Apply metadata filters
        if metadata_filters:
            for key, value in metadata_filters.items():
                query = query.eq(f"metadata->>{key}", value)

        result = query.execute()

        if not result.data:
            return []

        agent_cards = []
        for data in result.data:
            agent_card = AgentCard(
                agent_id=data["agent_id"],
                name=data["name"],
                description=data.get("description"),
                permissions=data.get("permissions", []),
                public_key=data["public_key"],
                endpoints=data.get("endpoints"),
                metadata=data.get("metadata"),
            )
            agent_cards.append(agent_card)

        return agent_cards

    @staticmethod
    def generate_rls_policy(table_name: str, policy_name: str) -> str:
        """Generate RLS policy for basic agent authentication.

        Args:
            table_name: Database table name
            policy_name: Policy name

        Returns:
            SQL for creating the RLS policy
        """
        return f"""
-- Enable RLS on the table
ALTER TABLE {table_name} ENABLE ROW LEVEL SECURITY;

-- Create policy for agent authentication
CREATE POLICY {policy_name} ON {table_name}
FOR ALL
USING (
  auth.jwt() ->> 'sub' IS NOT NULL
  AND EXISTS (
    SELECT 1 FROM agent_cards
    WHERE agent_id = auth.jwt() ->> 'sub'
  )
);
        """.strip()

    @staticmethod
    def generate_agent_specific_rls_policy(
        table_name: str, policy_name: str, agent_id_column: str = "agent_id"
    ) -> str:
        """Generate RLS policy for agent-specific access.

        Args:
            table_name: Database table name
            policy_name: Policy name
            agent_id_column: Column containing agent ID

        Returns:
            SQL for creating the RLS policy
        """
        return f"""
-- Enable RLS on the table
ALTER TABLE {table_name} ENABLE ROW LEVEL SECURITY;

-- Create policy for agent-specific access
CREATE POLICY {policy_name} ON {table_name}
FOR ALL
USING (
  {agent_id_column} = auth.jwt() ->> 'sub'
);
        """.strip()

    @staticmethod
    def generate_permission_based_rls_policy(
        table_name: str, policy_name: str, required_permission: str
    ) -> str:
        """Generate RLS policy for permission-based access.

        Args:
            table_name: Database table name
            policy_name: Policy name
            required_permission: Required permission

        Returns:
            SQL for creating the RLS policy
        """
        return f"""
-- Enable RLS on the table
ALTER TABLE {table_name} ENABLE ROW LEVEL SECURITY;

-- Create policy for permission-based access
CREATE POLICY {policy_name} ON {table_name}
FOR ALL
USING (
  auth.jwt() -> 'permissions' ? '{required_permission}'
);
        """.strip()
