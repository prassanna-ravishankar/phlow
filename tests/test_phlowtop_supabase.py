"""Tests for phlowtop Supabase client wrapper."""

from unittest.mock import Mock, patch

import pytest

from src.phlow.phlowtop.config import PhlowTopConfig
from src.phlow.phlowtop.supabase_client import SupabaseMonitor


class TestSupabaseMonitor:
    """Test phlowtop Supabase client wrapper."""

    @pytest.fixture
    def mock_config(self):
        """Create a mock configuration."""
        config = Mock(spec=PhlowTopConfig)
        config.supabase_url = "https://test.supabase.co"
        config.supabase_anon_key = "test-anon-key"
        config.connection_timeout_ms = 5000
        config.max_messages_per_task = 1000
        return config

    def create_monitor_with_mock_client(self, mock_config):
        """Helper to create monitor with mocked client."""
        monitor = SupabaseMonitor(mock_config)
        mock_client = Mock()
        monitor.client = mock_client
        return monitor, mock_client

    def test_initialization(self, mock_config):
        """Test SupabaseMonitor initialization."""
        monitor = SupabaseMonitor(mock_config)

        assert monitor.config == mock_config
        assert monitor.client is None  # Client is None until connect() is called
        assert monitor.is_connected is False

    @pytest.mark.asyncio
    async def test_connect_success(self, mock_config):
        """Test successful connection to Supabase."""
        with patch(
            "src.phlow.phlowtop.supabase_client.create_client"
        ) as mock_create_client:
            mock_client = Mock()
            mock_table = Mock()
            mock_select = Mock()
            mock_limit = Mock()
            mock_execute = Mock()

            # Chain the mock calls for table().select().limit().execute()
            mock_execute.return_value = Mock(data=[])
            mock_limit.execute = mock_execute
            mock_select.limit.return_value = mock_limit
            mock_table.select.return_value = mock_select
            mock_client.table.return_value = mock_table

            mock_create_client.return_value = mock_client

            monitor = SupabaseMonitor(mock_config)
            result = await monitor.connect()

            assert result is True
            assert monitor.is_connected is True
            mock_create_client.assert_called_once_with(
                mock_config.supabase_url, mock_config.supabase_anon_key
            )

    @pytest.mark.asyncio
    async def test_connect_failure(self, mock_config):
        """Test connection failure to Supabase."""
        with patch(
            "src.phlow.phlowtop.supabase_client.create_client"
        ) as mock_create_client:
            # Make create_client raise an exception
            mock_create_client.side_effect = Exception("Connection failed")

            monitor = SupabaseMonitor(mock_config)
            result = await monitor.connect()

            assert result is False
            assert monitor.is_connected is False

    @pytest.mark.asyncio
    async def test_fetch_agents(self, mock_config):
        """Test fetching agents data."""
        monitor = SupabaseMonitor(mock_config)

        # Mock agents data
        mock_agents_data = [
            {
                "agent_id": "agent-1",
                "name": "Test Agent 1",
                "status": "ONLINE",
                "active_tasks": 2,
                "service_url": "https://agent1.example.com",
                "created_at": "2024-01-01T00:00:00Z",
                "last_heartbeat": "2024-01-01T12:00:00Z",
            }
        ]

        # Create mock client and set it on monitor
        mock_client = Mock()
        mock_table = Mock()
        mock_select = Mock()
        mock_execute = Mock()

        mock_execute.return_value = Mock(data=mock_agents_data)
        mock_select.execute = mock_execute
        mock_table.select.return_value = mock_select
        mock_client.table.return_value = mock_table

        monitor.client = mock_client

        result = await monitor.fetch_agents()

        assert result == mock_agents_data
        mock_client.table.assert_called_once_with("agent_monitoring_summary")

    @pytest.mark.asyncio
    async def test_fetch_tasks(self, mock_config):
        """Test fetching tasks data."""
        monitor = SupabaseMonitor(mock_config)

        agent_id = "agent-1"
        mock_tasks_data = [
            {
                "task_id": "task-1",
                "agent_id": "agent-1",
                "client_agent_id": "client-1",
                "task_type": "process_data",
                "status": "COMPLETED",
                "created_at": "2024-01-01T10:00:00Z",
            }
        ]

        # Create mock client chain
        mock_client = Mock()
        mock_table = Mock()
        mock_select = Mock()
        mock_order = Mock()
        mock_limit = Mock()
        mock_eq = Mock()
        mock_execute = Mock()

        mock_execute.return_value = Mock(data=mock_tasks_data)
        mock_eq.execute = mock_execute
        mock_limit.eq.return_value = mock_eq
        mock_order.limit.return_value = mock_limit
        mock_select.order.return_value = mock_order
        mock_table.select.return_value = mock_select
        mock_client.table.return_value = mock_table

        monitor.client = mock_client

        result = await monitor.fetch_tasks(agent_id)

        assert result == mock_tasks_data
        mock_client.table.assert_called_once_with("phlow_tasks")

    @pytest.mark.asyncio
    async def test_fetch_messages(self, mock_config):
        """Test fetching messages data."""
        monitor, mock_client = self.create_monitor_with_mock_client(mock_config)

        task_id = "task-1"
        mock_messages_data = [
            {
                "message_id": "msg-1",
                "task_id": "task-1",
                "source_agent_id": "agent-1",
                "target_agent_id": "agent-2",
                "message_type": "request",
                "content": {"action": "process"},
                "created_at": "2024-01-01T10:00:00Z",
            }
        ]

        # Mock the query chain
        mock_table = Mock()
        mock_select = Mock()
        mock_eq = Mock()
        mock_order = Mock()
        mock_limit = Mock()
        mock_execute = Mock()

        mock_execute.return_value = Mock(data=mock_messages_data)
        mock_limit.execute = mock_execute
        mock_order.limit.return_value = mock_limit
        mock_eq.order.return_value = mock_order
        mock_select.eq.return_value = mock_eq
        mock_table.select.return_value = mock_select
        mock_client.table.return_value = mock_table

        result = await monitor.fetch_messages(task_id)

        assert result == mock_messages_data
        mock_client.table.assert_called_once_with("phlow_messages")

    @pytest.mark.asyncio
    async def test_get_summary_stats(self, mock_config):
        """Test getting summary statistics."""
        monitor, mock_client = self.create_monitor_with_mock_client(mock_config)

        # Mock multiple queries for the stats

        # Mock agents query
        mock_agents_result = Mock(
            data=[
                {
                    "agent_id": "1",
                    "status": "ONLINE",
                    "last_heartbeat": "2024-01-01T12:00:00Z",
                },
                {
                    "agent_id": "2",
                    "status": "IDLE",
                    "last_heartbeat": "2024-01-01T11:59:00Z",
                },
            ]
        )

        # Mock tasks query
        mock_tasks_result = Mock(data=[{"task_id": "t1"}, {"task_id": "t2"}])

        # Mock messages query
        mock_messages_result = Mock(data=[{"message_id": "m1"}])

        # Mock errors query
        mock_errors_result = Mock(data=[])

        def table_side_effect(table_name):
            mock_query = Mock()
            if table_name == "agent_cards":
                mock_query.select().execute.return_value = mock_agents_result
            elif table_name == "phlow_tasks":
                if hasattr(mock_query.select().in_(), "execute"):
                    mock_query.select().in_().execute.return_value = mock_tasks_result
                else:
                    mock_query.select().eq().gte().execute.return_value = (
                        mock_errors_result
                    )

            elif table_name == "phlow_messages":
                mock_query.select().gte().execute.return_value = mock_messages_result
            return mock_query

        mock_client.table.side_effect = table_side_effect

        result = await monitor.get_summary_stats()

        assert "agents_online" in result
        assert "agents_total" in result
        assert "tasks_active" in result
        assert "messages_per_minute" in result
        assert "errors_last_hour" in result

    @pytest.mark.asyncio
    async def test_start_realtime_subscriptions(self, mock_config):
        """Test starting realtime subscriptions."""
        monitor, mock_client = self.create_monitor_with_mock_client(mock_config)

        await monitor.start_realtime_subscriptions()

        # Should complete without errors (implementation is placeholder)
        assert monitor.client is not None

    @pytest.mark.asyncio
    async def test_close(self, mock_config):
        """Test closing connections."""
        monitor, mock_client = self.create_monitor_with_mock_client(mock_config)
        monitor.is_connected = True

        await monitor.close()

        assert monitor.is_connected is False
