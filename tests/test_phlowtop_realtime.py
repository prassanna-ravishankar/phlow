"""Tests for phlowtop real-time subscriptions."""

from unittest.mock import AsyncMock, Mock, patch

import pytest

from src.phlow.phlowtop.config import PhlowTopConfig
from src.phlow.phlowtop.supabase_client import SupabaseMonitor


@pytest.fixture
def mock_config():
    """Create a mock PhlowTopConfig."""
    config = Mock(spec=PhlowTopConfig)
    config.supabase_url = "https://test.supabase.co"
    config.supabase_anon_key = "test-key"
    config.refresh_rate = 1000
    config.max_messages_per_task = 100
    return config


@pytest.fixture
def mock_supabase_client():
    """Create a mock Supabase client."""
    client = Mock()

    # Mock realtime channel
    mock_channel = Mock()
    mock_channel.on = Mock()
    mock_channel.subscribe = AsyncMock()
    mock_channel.unsubscribe = AsyncMock()

    client.realtime.channel.return_value = mock_channel

    return client, mock_channel


class TestSupabaseMonitorRealtime:
    """Test real-time functionality of SupabaseMonitor."""

    def test_initialization(self, mock_config):
        """Test SupabaseMonitor initialization with realtime state."""
        monitor = SupabaseMonitor(mock_config)

        assert monitor.config == mock_config
        assert monitor.callbacks == {}
        assert monitor.realtime_channel is None
        assert monitor.subscription_active is False

    def test_register_callback(self, mock_config):
        """Test callback registration."""
        monitor = SupabaseMonitor(mock_config)

        callback1 = Mock()
        callback2 = Mock()

        # Register callbacks for different event types
        monitor.register_callback("agent_change", callback1)
        monitor.register_callback("task_change", callback2)
        monitor.register_callback("agent_change", callback2)  # Multiple for same event

        assert "agent_change" in monitor.callbacks
        assert "task_change" in monitor.callbacks
        assert len(monitor.callbacks["agent_change"]) == 2
        assert len(monitor.callbacks["task_change"]) == 1
        assert callback1 in monitor.callbacks["agent_change"]
        assert callback2 in monitor.callbacks["agent_change"]
        assert callback2 in monitor.callbacks["task_change"]

    @pytest.mark.asyncio
    async def test_start_realtime_subscriptions_success(
        self, mock_config, mock_supabase_client
    ):
        """Test successful start of real-time subscriptions."""
        client, mock_channel = mock_supabase_client

        monitor = SupabaseMonitor(mock_config)
        monitor.client = client

        await monitor.start_realtime_subscriptions()

        # Verify channel creation and subscriptions
        client.realtime.channel.assert_called_once_with("phlowtop")
        assert mock_channel.on.call_count == 3  # 3 table subscriptions
        mock_channel.subscribe.assert_called_once()
        assert monitor.subscription_active is True
        assert monitor.realtime_channel == mock_channel

    @pytest.mark.asyncio
    async def test_start_realtime_subscriptions_no_client(self, mock_config):
        """Test start subscriptions without client."""
        monitor = SupabaseMonitor(mock_config)
        monitor.client = None

        await monitor.start_realtime_subscriptions()

        assert monitor.subscription_active is False
        assert monitor.realtime_channel is None

    @pytest.mark.asyncio
    async def test_start_realtime_subscriptions_already_active(
        self, mock_config, mock_supabase_client
    ):
        """Test start subscriptions when already active."""
        client, mock_channel = mock_supabase_client

        monitor = SupabaseMonitor(mock_config)
        monitor.client = client
        monitor.subscription_active = True

        await monitor.start_realtime_subscriptions()

        # Should not create new subscriptions
        client.realtime.channel.assert_not_called()

    @pytest.mark.asyncio
    async def test_start_realtime_subscriptions_error(
        self, mock_config, mock_supabase_client
    ):
        """Test error handling during subscription start."""
        client, mock_channel = mock_supabase_client
        mock_channel.subscribe.side_effect = Exception("Connection failed")

        monitor = SupabaseMonitor(mock_config)
        monitor.client = client

        await monitor.start_realtime_subscriptions()

        assert monitor.subscription_active is False

    @pytest.mark.asyncio
    async def test_stop_realtime_subscriptions_success(
        self, mock_config, mock_supabase_client
    ):
        """Test successful stop of real-time subscriptions."""
        client, mock_channel = mock_supabase_client

        monitor = SupabaseMonitor(mock_config)
        monitor.client = client
        monitor.realtime_channel = mock_channel
        monitor.subscription_active = True

        await monitor.stop_realtime_subscriptions()

        mock_channel.unsubscribe.assert_called_once()
        assert monitor.subscription_active is False

    @pytest.mark.asyncio
    async def test_stop_realtime_subscriptions_not_active(self, mock_config):
        """Test stop subscriptions when not active."""
        monitor = SupabaseMonitor(mock_config)
        monitor.subscription_active = False

        await monitor.stop_realtime_subscriptions()

        # Should not attempt to unsubscribe

    @pytest.mark.asyncio
    async def test_stop_realtime_subscriptions_error(
        self, mock_config, mock_supabase_client
    ):
        """Test error handling during subscription stop."""
        client, mock_channel = mock_supabase_client
        mock_channel.unsubscribe.side_effect = Exception("Unsubscribe failed")

        monitor = SupabaseMonitor(mock_config)
        monitor.client = client
        monitor.realtime_channel = mock_channel
        monitor.subscription_active = True

        await monitor.stop_realtime_subscriptions()

        # Should handle error gracefully

    def test_handle_agent_change(self, mock_config):
        """Test agent change event handling."""
        monitor = SupabaseMonitor(mock_config)

        callback1 = Mock()
        callback2 = Mock()
        monitor.register_callback("agent_change", callback1)
        monitor.register_callback("agent_change", callback2)

        payload = {
            "eventType": "UPDATE",
            "new": {"agent_id": "agent-1", "status": "WORKING"},
            "old": {"agent_id": "agent-1", "status": "IDLE"},
        }

        # Mock asyncio.create_task to capture the coroutines
        with patch("asyncio.create_task") as mock_create_task:
            monitor._handle_agent_change(payload)

            # Should create tasks for both callbacks
            assert mock_create_task.call_count == 2

    def test_handle_task_change(self, mock_config):
        """Test task change event handling."""
        monitor = SupabaseMonitor(mock_config)

        callback = Mock()
        monitor.register_callback("task_change", callback)

        payload = {
            "eventType": "INSERT",
            "new": {"task_id": "task-1", "status": "SUBMITTED", "agent_id": "agent-1"},
        }

        with patch("asyncio.create_task") as mock_create_task:
            monitor._handle_task_change(payload)

            # Should create task for callback
            mock_create_task.assert_called_once()

    def test_handle_message_change(self, mock_config):
        """Test message change event handling."""
        monitor = SupabaseMonitor(mock_config)

        callback = Mock()
        monitor.register_callback("message_change", callback)

        payload = {
            "eventType": "INSERT",
            "new": {
                "message_id": "msg-1",
                "task_id": "task-1",
                "source_agent_id": "agent-1",
                "target_agent_id": "agent-2",
            },
        }

        with patch("asyncio.create_task") as mock_create_task:
            monitor._handle_message_change(payload)

            # Should create task for callback
            mock_create_task.assert_called_once()

    @pytest.mark.asyncio
    async def test_run_callback_async(self, mock_config):
        """Test running async callback."""
        monitor = SupabaseMonitor(mock_config)

        async_callback = AsyncMock()
        payload = {"test": "data"}

        await monitor._run_callback(async_callback, payload)

        async_callback.assert_called_once_with(payload)

    @pytest.mark.asyncio
    async def test_run_callback_sync(self, mock_config):
        """Test running sync callback."""
        monitor = SupabaseMonitor(mock_config)

        sync_callback = Mock()
        payload = {"test": "data"}

        await monitor._run_callback(sync_callback, payload)

        sync_callback.assert_called_once_with(payload)

    @pytest.mark.asyncio
    async def test_run_callback_error(self, mock_config):
        """Test callback error handling."""
        monitor = SupabaseMonitor(mock_config)

        error_callback = Mock(side_effect=Exception("Callback failed"))
        payload = {"test": "data"}

        # Should not raise exception
        await monitor._run_callback(error_callback, payload)

        error_callback.assert_called_once_with(payload)

    def test_handle_change_error(self, mock_config):
        """Test error handling in change handlers."""
        monitor = SupabaseMonitor(mock_config)

        # Register callback that will cause error
        error_callback = Mock()
        monitor.register_callback("agent_change", error_callback)

        # Mock create_task to raise error
        with patch(
            "asyncio.create_task", side_effect=Exception("Task creation failed")
        ):
            # Should not raise exception
            monitor._handle_agent_change({"eventType": "UPDATE"})

    @pytest.mark.asyncio
    async def test_close_with_subscriptions(self, mock_config, mock_supabase_client):
        """Test close method stops subscriptions."""
        client, mock_channel = mock_supabase_client

        monitor = SupabaseMonitor(mock_config)
        monitor.client = client
        monitor.realtime_channel = mock_channel
        monitor.subscription_active = True
        monitor.is_connected = True

        await monitor.close()

        # Should stop subscriptions and cleanup
        mock_channel.unsubscribe.assert_called_once()
        assert monitor.subscription_active is False
        assert monitor.is_connected is False
        assert monitor.client is None


class TestRealtimeIntegration:
    """Test integration between realtime subscriptions and app components."""

    @pytest.mark.asyncio
    async def test_subscription_flow(self, mock_config, mock_supabase_client):
        """Test complete subscription flow."""
        client, mock_channel = mock_supabase_client

        monitor = SupabaseMonitor(mock_config)
        monitor.client = client

        # Register callbacks
        agent_callback = AsyncMock()
        task_callback = AsyncMock()
        message_callback = AsyncMock()

        monitor.register_callback("agent_change", agent_callback)
        monitor.register_callback("task_change", task_callback)
        monitor.register_callback("message_change", message_callback)

        # Start subscriptions
        await monitor.start_realtime_subscriptions()

        assert monitor.subscription_active is True
        assert len(monitor.callbacks) == 3

        # Stop subscriptions
        await monitor.stop_realtime_subscriptions()

        assert monitor.subscription_active is False

    def test_multiple_callbacks_same_event(self, mock_config):
        """Test multiple callbacks for the same event type."""
        monitor = SupabaseMonitor(mock_config)

        callback1 = Mock()
        callback2 = Mock()
        callback3 = Mock()

        # Register multiple callbacks for agent changes
        monitor.register_callback("agent_change", callback1)
        monitor.register_callback("agent_change", callback2)
        monitor.register_callback("agent_change", callback3)

        assert len(monitor.callbacks["agent_change"]) == 3

        # Trigger event
        payload = {"eventType": "UPDATE", "new": {"agent_id": "test"}}

        with patch("asyncio.create_task") as mock_create_task:
            monitor._handle_agent_change(payload)

            # Should create tasks for all 3 callbacks
            assert mock_create_task.call_count == 3
