"""Tests for supabase_helpers module."""

from unittest.mock import MagicMock

import pytest

from phlow.supabase_helpers import SupabaseHelpers
from phlow.types import AgentCard


def _make_supabase_mock():
    return MagicMock()


def _make_agent_card():
    return AgentCard(
        name="test-agent",
        description="Test agent",
        agent_id="agent-001",
        permissions=["read", "write"],
        public_key="pk-123",
        endpoints={"task": "/tasks/send"},
        metadata={"version": "1.0"},
    )


def _make_agent_data():
    return {
        "agent_id": "agent-001",
        "name": "test-agent",
        "description": "Test agent",
        "permissions": ["read", "write"],
        "public_key": "pk-123",
        "endpoints": {"task": "/tasks/send"},
        "metadata": {"version": "1.0"},
    }


class TestRegisterAgentCard:
    @pytest.mark.asyncio
    async def test_registers_successfully(self):
        supabase = _make_supabase_mock()
        supabase.table.return_value.upsert.return_value.execute.return_value = (
            MagicMock(data=[{"agent_id": "agent-001"}])
        )

        helpers = SupabaseHelpers(supabase)
        await helpers.register_agent_card(_make_agent_card())
        supabase.table.assert_called_with("agent_cards")

    @pytest.mark.asyncio
    async def test_raises_on_failure(self):
        supabase = _make_supabase_mock()
        result = MagicMock()
        result.data = None
        supabase.table.return_value.upsert.return_value.execute.return_value = result

        helpers = SupabaseHelpers(supabase)
        with pytest.raises(Exception, match="Failed to register"):
            await helpers.register_agent_card(_make_agent_card())

    def test_register_sync(self):
        supabase = _make_supabase_mock()
        supabase.table.return_value.upsert.return_value.execute.return_value = (
            MagicMock(data=[{"agent_id": "agent-001"}])
        )

        helpers = SupabaseHelpers(supabase)
        helpers.register_agent_card_sync(_make_agent_card())
        supabase.table.assert_called_with("agent_cards")

    def test_register_sync_raises_on_failure(self):
        supabase = _make_supabase_mock()
        result = MagicMock()
        result.data = None
        supabase.table.return_value.upsert.return_value.execute.return_value = result

        helpers = SupabaseHelpers(supabase)
        with pytest.raises(Exception, match="Failed to register"):
            helpers.register_agent_card_sync(_make_agent_card())


class TestGetAgentCard:
    @pytest.mark.asyncio
    async def test_returns_agent_card(self):
        supabase = _make_supabase_mock()
        supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(
            data=_make_agent_data()
        )

        helpers = SupabaseHelpers(supabase)
        card = await helpers.get_agent_card("agent-001")
        assert card is not None
        assert card.name == "test-agent"
        assert card.agent_id == "agent-001"

    @pytest.mark.asyncio
    async def test_returns_none_when_not_found(self):
        supabase = _make_supabase_mock()
        supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(
            data=None
        )

        helpers = SupabaseHelpers(supabase)
        card = await helpers.get_agent_card("nonexistent")
        assert card is None

    def test_get_sync(self):
        supabase = _make_supabase_mock()
        supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(
            data=_make_agent_data()
        )

        helpers = SupabaseHelpers(supabase)
        card = helpers.get_agent_card_sync("agent-001")
        assert card is not None
        assert card.name == "test-agent"

    def test_get_sync_returns_none(self):
        supabase = _make_supabase_mock()
        supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(
            data=None
        )

        helpers = SupabaseHelpers(supabase)
        card = helpers.get_agent_card_sync("nonexistent")
        assert card is None


class TestListAgentCards:
    @pytest.mark.asyncio
    async def test_lists_all_cards(self):
        supabase = _make_supabase_mock()
        supabase.table.return_value.select.return_value.execute.return_value = (
            MagicMock(
                data=[
                    _make_agent_data(),
                    {**_make_agent_data(), "agent_id": "agent-002", "name": "agent-2"},
                ]
            )
        )

        helpers = SupabaseHelpers(supabase)
        cards = await helpers.list_agent_cards()
        assert len(cards) == 2

    @pytest.mark.asyncio
    async def test_returns_empty_list(self):
        supabase = _make_supabase_mock()
        supabase.table.return_value.select.return_value.execute.return_value = (
            MagicMock(data=None)
        )

        helpers = SupabaseHelpers(supabase)
        cards = await helpers.list_agent_cards()
        assert cards == []

    @pytest.mark.asyncio
    async def test_filters_by_permissions(self):
        supabase = _make_supabase_mock()
        query_mock = MagicMock()
        supabase.table.return_value.select.return_value = query_mock
        query_mock.contains.return_value = query_mock
        query_mock.execute.return_value = MagicMock(data=[_make_agent_data()])

        helpers = SupabaseHelpers(supabase)
        cards = await helpers.list_agent_cards(permissions=["read"])
        assert len(cards) == 1
        query_mock.contains.assert_called()

    @pytest.mark.asyncio
    async def test_filters_by_metadata(self):
        supabase = _make_supabase_mock()
        query_mock = MagicMock()
        supabase.table.return_value.select.return_value = query_mock
        query_mock.eq.return_value = query_mock
        query_mock.execute.return_value = MagicMock(data=[_make_agent_data()])

        helpers = SupabaseHelpers(supabase)
        cards = await helpers.list_agent_cards(metadata_filters={"version": "1.0"})
        assert len(cards) == 1

    def test_list_sync(self):
        supabase = _make_supabase_mock()
        supabase.table.return_value.select.return_value.execute.return_value = (
            MagicMock(data=[_make_agent_data()])
        )

        helpers = SupabaseHelpers(supabase)
        cards = helpers.list_agent_cards_sync()
        assert len(cards) == 1

    def test_list_sync_empty(self):
        supabase = _make_supabase_mock()
        supabase.table.return_value.select.return_value.execute.return_value = (
            MagicMock(data=None)
        )

        helpers = SupabaseHelpers(supabase)
        cards = helpers.list_agent_cards_sync()
        assert cards == []


class TestGenerateRlsPolicy:
    def test_basic_policy(self):
        sql = SupabaseHelpers.generate_rls_policy("my_table", "my_policy")
        assert "my_table" in sql
        assert "my_policy" in sql
        assert "ENABLE ROW LEVEL SECURITY" in sql
        assert "agent_cards" in sql

    def test_agent_specific_policy(self):
        sql = SupabaseHelpers.generate_agent_specific_rls_policy(
            "my_table", "agent_policy"
        )
        assert "agent_id" in sql
        assert "auth.jwt()" in sql

    def test_agent_specific_custom_column(self):
        sql = SupabaseHelpers.generate_agent_specific_rls_policy(
            "my_table", "policy", agent_id_column="owner_id"
        )
        assert "owner_id" in sql

    def test_permission_based_policy(self):
        sql = SupabaseHelpers.generate_permission_based_rls_policy(
            "my_table", "perm_policy", "admin:write"
        )
        assert "admin:write" in sql
        assert "permissions" in sql
