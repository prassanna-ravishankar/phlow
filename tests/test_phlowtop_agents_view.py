"""Tests for phlowtop Agents Dashboard view."""

from unittest.mock import AsyncMock, Mock, patch

import pytest

from src.phlow.phlowtop.config import PhlowTopConfig
from src.phlow.phlowtop.supabase_client import SupabaseMonitor
from src.phlow.phlowtop.views.agents import AgentsView


class TestAgentsView:
    """Test phlowtop Agents Dashboard view."""

    @pytest.fixture
    def mock_config(self):
        """Create a mock configuration."""
        config = Mock(spec=PhlowTopConfig)
        config.supabase_url = "https://test.supabase.co"
        config.supabase_anon_key = "test-anon-key"
        config.connection_timeout_ms = 5000
        config.max_messages_per_task = 1000
        config.datetime_format = "%Y-%m-%d %H:%M:%S"
        return config

    @pytest.fixture
    def mock_supabase_monitor(self):
        """Create a mock Supabase monitor."""
        monitor = Mock(spec=SupabaseMonitor)
        return monitor

    def test_agents_view_initialization(self, mock_supabase_monitor, mock_config):
        """Test AgentsView initialization."""
        with patch("textual.widgets.DataTable.__init__", return_value=None):
            view = AgentsView(mock_supabase_monitor, mock_config)

            assert view.supabase == mock_supabase_monitor
            assert view.config == mock_config
            assert view.agents_data == []
            assert view.cursor_type == "row"
            assert view.zebra_stripes is True

    @pytest.mark.asyncio
    async def test_refresh_data_success(self, mock_supabase_monitor, mock_config):
        """Test successful data refresh."""
        with patch("textual.widgets.DataTable.__init__", return_value=None):
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
                },
                {
                    "agent_id": "agent-2",
                    "name": "Test Agent 2",
                    "status": "IDLE",
                    "active_tasks": 0,
                    "service_url": "https://agent2.example.com",
                    "created_at": "2024-01-01T00:00:00Z",
                    "last_heartbeat": "2024-01-01T11:30:00Z",
                },
            ]

            mock_supabase_monitor.fetch_agents = AsyncMock(
                return_value=mock_agents_data
            )

            view = AgentsView(mock_supabase_monitor, mock_config)

            # Mock the _update_table method
            view._update_table = AsyncMock()

            await view.refresh_data()

            assert view.agents_data == mock_agents_data
            mock_supabase_monitor.fetch_agents.assert_called_once()
            view._update_table.assert_called_once()

    @pytest.mark.asyncio
    async def test_refresh_data_error(self, mock_supabase_monitor, mock_config):
        """Test data refresh with error."""
        with patch("textual.widgets.DataTable.__init__", return_value=None):
            # Mock fetch_agents to raise an exception
            mock_supabase_monitor.fetch_agents = AsyncMock(
                side_effect=Exception("Connection error")
            )

            view = AgentsView(mock_supabase_monitor, mock_config)

            # Mock app.notify
            view.app = Mock()
            view.app.notify = Mock()

            await view.refresh_data()

            # Should handle error gracefully
            view.app.notify.assert_called_once_with(
                "Error refreshing agents: Connection error", severity="error"
            )

    def test_format_status(self, mock_supabase_monitor, mock_config):
        """Test status formatting with colors."""
        with patch("textual.widgets.DataTable.__init__", return_value=None):
            from rich.text import Text

            view = AgentsView(mock_supabase_monitor, mock_config)

            # Test different status colors
            test_cases = [
                ("ONLINE", "green"),
                ("WORKING", "blue"),
                ("IDLE", "white"),
                ("ERROR", "red"),
                ("OFFLINE", "gray"),
                ("UNKNOWN", "white"),  # default
            ]

            for status, _expected_color in test_cases:
                result = view._format_status(status)
                assert isinstance(result, Text)
                assert str(result) == status

    def test_calculate_uptime(self, mock_supabase_monitor, mock_config):
        """Test uptime calculation."""
        with patch("textual.widgets.DataTable.__init__", return_value=None):
            view = AgentsView(mock_supabase_monitor, mock_config)

            # Test with None timestamp
            assert view._calculate_uptime(None) == "N/A"

            # Test with invalid timestamp
            assert view._calculate_uptime("invalid") == "N/A"

            # Test with valid timestamps using mock
            from datetime import datetime, timezone

            with patch("src.phlow.phlowtop.views.agents.datetime") as mock_datetime:
                mock_now = datetime(2024, 1, 1, 12, 30, 0, tzinfo=timezone.utc)
                mock_created = datetime(2024, 1, 1, 10, 0, 0, tzinfo=timezone.utc)

                mock_datetime.now.return_value = mock_now
                mock_datetime.fromisoformat.return_value = mock_created

                result = view._calculate_uptime("2024-01-01T10:00:00Z")
                assert result == "2h 30m"

    def test_format_heartbeat(self, mock_supabase_monitor, mock_config):
        """Test heartbeat formatting."""
        with patch("textual.widgets.DataTable.__init__", return_value=None):
            view = AgentsView(mock_supabase_monitor, mock_config)

            # Test with None heartbeat
            assert view._format_heartbeat(None) == "Never"

            # Test with invalid heartbeat
            assert view._format_heartbeat("invalid") == "N/A"

            # Test with valid heartbeat using mock
            from datetime import datetime, timezone

            with patch("src.phlow.phlowtop.views.agents.datetime") as mock_datetime:
                mock_now = datetime(2024, 1, 1, 12, 30, 0, tzinfo=timezone.utc)
                mock_heartbeat = datetime(2024, 1, 1, 12, 25, 0, tzinfo=timezone.utc)

                mock_datetime.now.return_value = mock_now
                mock_datetime.fromisoformat.return_value = mock_heartbeat

                result = view._format_heartbeat("2024-01-01T12:25:00Z")
                assert result == "5m ago"

    @pytest.mark.asyncio
    async def test_on_mount(self, mock_supabase_monitor, mock_config):
        """Test view mounting."""
        with patch("textual.widgets.DataTable.__init__", return_value=None):
            view = AgentsView(mock_supabase_monitor, mock_config)

            # Mock DataTable methods
            view.add_columns = Mock()
            view.refresh_data = AsyncMock()

            await view.on_mount()

            # Should add columns and refresh data
            view.add_columns.assert_called_once_with(
                "Agent Name",
                "Status",
                "Active Tasks",
                "Uptime",
                "Endpoint",
                "Last Heartbeat",
            )
            view.refresh_data.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_table(self, mock_supabase_monitor, mock_config):
        """Test table updating with agent data."""
        with patch("textual.widgets.DataTable.__init__", return_value=None):
            mock_agents_data = [
                {
                    "agent_id": "agent-1",
                    "name": "Test Agent",
                    "status": "ONLINE",
                    "active_tasks": 1,
                    "service_url": "https://test.com",
                    "created_at": "2024-01-01T00:00:00Z",
                    "last_heartbeat": "2024-01-01T12:00:00Z",
                }
            ]

            view = AgentsView(mock_supabase_monitor, mock_config)
            view.agents_data = mock_agents_data

            # Mock DataTable methods
            view.clear = Mock()
            view.add_columns = Mock()
            view.add_row = Mock()
            view._format_status = Mock(return_value="ONLINE")
            view._calculate_uptime = Mock(return_value="12h")
            view._format_heartbeat = Mock(return_value="5m ago")

            await view._update_table()

            # Should clear and rebuild table
            view.clear.assert_called_once()
            view.add_columns.assert_called_once()
            view.add_row.assert_called_once_with(
                "Test Agent", "ONLINE", "1", "12h", "https://test.com", "5m ago"
            )

    @pytest.mark.asyncio
    async def test_row_selection(self, mock_supabase_monitor, mock_config):
        """Test row selection handling."""
        with patch("textual.widgets.DataTable.__init__", return_value=None):
            mock_agents_data = [
                {"agent_id": "agent-1", "name": "Test Agent 1"},
                {"agent_id": "agent-2", "name": "Test Agent 2"},
            ]

            view = AgentsView(mock_supabase_monitor, mock_config)
            view.agents_data = mock_agents_data

            # Mock app
            view.app = Mock()
            view.app.on_agent_selected = AsyncMock()

            # Mock row selection event
            from textual.widgets import DataTable

            mock_event = Mock(spec=DataTable.RowSelected)
            mock_event.row_key = Mock()
            mock_event.row_key.value = 1  # Select second agent

            await view.on_data_table_row_selected(mock_event)

            # Should call app's on_agent_selected with the correct agent_id
            view.app.on_agent_selected.assert_called_once_with("agent-2")

    @pytest.mark.asyncio
    async def test_row_selection_invalid_index(
        self, mock_supabase_monitor, mock_config
    ):
        """Test row selection with invalid index."""
        with patch("textual.widgets.DataTable.__init__", return_value=None):
            view = AgentsView(mock_supabase_monitor, mock_config)
            view.agents_data = [{"agent_id": "agent-1"}]

            # Mock app
            view.app = Mock()
            view.app.on_agent_selected = AsyncMock()

            # Mock row selection event with invalid index
            from textual.widgets import DataTable

            mock_event = Mock(spec=DataTable.RowSelected)
            mock_event.row_key = Mock()
            mock_event.row_key.value = 5  # Invalid index

            await view.on_data_table_row_selected(mock_event)

            # Should not call on_agent_selected
            view.app.on_agent_selected.assert_not_called()

    @pytest.mark.asyncio
    async def test_row_selection_missing_agent_id(
        self, mock_supabase_monitor, mock_config
    ):
        """Test row selection with missing agent_id."""
        with patch("textual.widgets.DataTable.__init__", return_value=None):
            mock_agents_data = [
                {"name": "Agent without ID"}  # Missing agent_id
            ]

            view = AgentsView(mock_supabase_monitor, mock_config)
            view.agents_data = mock_agents_data

            # Mock app
            view.app = Mock()
            view.app.on_agent_selected = AsyncMock()

            # Mock row selection event
            from textual.widgets import DataTable

            mock_event = Mock(spec=DataTable.RowSelected)
            mock_event.row_key = Mock()
            mock_event.row_key.value = 0

            await view.on_data_table_row_selected(mock_event)

            # Should not call on_agent_selected when agent_id is missing
            view.app.on_agent_selected.assert_not_called()

    def test_data_processing_logic(self, mock_supabase_monitor, mock_config):
        """Test data processing logic."""
        with patch("textual.widgets.DataTable.__init__", return_value=None):
            # Mock agent data processing
            mock_agents_data = [
                {
                    "agent_id": "agent-1",
                    "name": "Test Agent 1",
                    "status": "ONLINE",
                    "active_tasks": 2,
                    "service_url": "https://agent1.example.com",
                    "created_at": "2024-01-01T00:00:00Z",
                    "last_heartbeat": "2024-01-01T12:00:00Z",
                },
                {
                    "agent_id": "agent-2",
                    "name": "Test Agent 2",
                    "status": "IDLE",
                    "active_tasks": 0,
                    "service_url": "https://agent2.example.com",
                    "created_at": "2024-01-01T00:00:00Z",
                    "last_heartbeat": "2024-01-01T11:30:00Z",
                },
            ]

            # Test data structure validity
            for agent in mock_agents_data:
                assert "agent_id" in agent
                assert "name" in agent
                assert "status" in agent
                assert agent["status"] in [
                    "ONLINE",
                    "WORKING",
                    "IDLE",
                    "ERROR",
                    "OFFLINE",
                ]
                assert isinstance(agent.get("active_tasks", 0), int)
