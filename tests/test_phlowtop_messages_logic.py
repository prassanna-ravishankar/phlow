"""Tests for phlowtop Messages view logic."""

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, Mock

import pytest
from rich.text import Text

from src.phlow.phlowtop.config import PhlowTopConfig
from src.phlow.phlowtop.supabase_client import SupabaseMonitor
from src.phlow.phlowtop.views.messages import MessagesView


@pytest.fixture
def mock_supabase():
    """Create a mock SupabaseMonitor."""
    mock = Mock(spec=SupabaseMonitor)
    mock.fetch_messages = AsyncMock()
    return mock


@pytest.fixture
def mock_config():
    """Create a mock PhlowTopConfig."""
    config = Mock(spec=PhlowTopConfig)
    config.refresh_rate = 1000
    config.max_messages_per_task = 100
    config.datetime_format = "%H:%M:%S"
    return config


@pytest.fixture
def sample_messages():
    """Sample message data for testing."""
    now = datetime.now(timezone.utc)
    return [
        {
            "message_id": "msg-001",
            "task_id": "task-123",
            "source_agent_id": "client-agent",
            "target_agent_id": "worker-agent",
            "message_type": "request",
            "content": {
                "task": "Analyze sales data",
                "data": {"Q4_sales": 150000, "Q3_sales": 120000},
            },
            "created_at": (now - timedelta(minutes=10)).isoformat(),
        },
        {
            "message_id": "msg-002",
            "task_id": "task-123",
            "source_agent_id": "worker-agent",
            "target_agent_id": "data-agent",
            "message_type": "delegation",
            "content": {
                "task": "Fetch historical sales data",
                "parameters": {"quarters": 4, "format": "json"},
            },
            "created_at": (now - timedelta(minutes=8)).isoformat(),
        },
        {
            "message_id": "msg-003",
            "task_id": "task-123",
            "source_agent_id": "data-agent",
            "target_agent_id": "worker-agent",
            "message_type": "response",
            "content": {
                "status": "completed",
                "data": {
                    "Q1_sales": 100000,
                    "Q2_sales": 110000,
                    "Q3_sales": 120000,
                    "Q4_sales": 150000,
                },
            },
            "created_at": (now - timedelta(minutes=5)).isoformat(),
        },
        {
            "message_id": "msg-004",
            "task_id": "task-123",
            "source_agent_id": "worker-agent",
            "target_agent_id": "client-agent",
            "message_type": "response",
            "content": {
                "status": "completed",
                "analysis": "Sales show 25% growth trend. Q4 performance exceeded expectations.",
                "recommendation": "Continue current marketing strategy",
            },
            "created_at": (now - timedelta(minutes=2)).isoformat(),
        },
    ]


class TestMessagesViewLogic:
    """Test the logic methods of MessagesView without UI framework dependencies."""

    def test_format_timestamp_valid(self, mock_supabase, mock_config):
        """Test timestamp formatting with valid input."""
        view = MessagesView(mock_supabase, mock_config)

        # Test with ISO timestamp
        timestamp = "2025-08-05T10:30:45.123456+00:00"
        result = view._format_timestamp(timestamp)
        assert "10:30:45" in result

    def test_format_timestamp_with_z(self, mock_supabase, mock_config):
        """Test timestamp formatting with Z suffix."""
        view = MessagesView(mock_supabase, mock_config)

        # Test with Z suffix
        timestamp = "2025-08-05T10:30:45.123456Z"
        result = view._format_timestamp(timestamp)
        assert "10:30:45" in result

    def test_format_timestamp_none(self, mock_supabase, mock_config):
        """Test timestamp formatting with None."""
        view = MessagesView(mock_supabase, mock_config)

        result = view._format_timestamp(None)
        assert result == "N/A"

    def test_format_timestamp_empty(self, mock_supabase, mock_config):
        """Test timestamp formatting with empty string."""
        view = MessagesView(mock_supabase, mock_config)

        result = view._format_timestamp("")
        assert result == "N/A"

    def test_format_timestamp_invalid(self, mock_supabase, mock_config):
        """Test timestamp formatting with invalid input."""
        view = MessagesView(mock_supabase, mock_config)

        invalid_timestamp = "not-a-timestamp"
        result = view._format_timestamp(invalid_timestamp)
        assert result == invalid_timestamp  # Falls back to original

    def test_format_content_empty(self, mock_supabase, mock_config):
        """Test content formatting with empty content."""
        view = MessagesView(mock_supabase, mock_config)

        result = view._format_content({})
        assert isinstance(result, Text)
        assert result.plain == "(empty)"
        assert "dim" in str(result.style)

    def test_format_content_none(self, mock_supabase, mock_config):
        """Test content formatting with None content."""
        view = MessagesView(mock_supabase, mock_config)

        result = view._format_content(None)
        assert isinstance(result, Text)
        assert result.plain == "(empty)"

    def test_format_content_simple(self, mock_supabase, mock_config):
        """Test content formatting with simple content."""
        view = MessagesView(mock_supabase, mock_config)

        content = {"message": "Hello", "status": "ok"}
        result = view._format_content(content)

        assert isinstance(result, Text)
        assert "Hello" in result.plain
        assert "status" in result.plain
        assert "ok" in result.plain

    def test_format_content_complex(self, mock_supabase, mock_config):
        """Test content formatting with complex nested content."""
        view = MessagesView(mock_supabase, mock_config)

        content = {"task": "complex_analysis", "status": "completed"}
        result = view._format_content(content)

        assert isinstance(result, Text)
        assert "complex_analysis" in result.plain
        assert "completed" in result.plain

    def test_format_content_large_truncated(self, mock_supabase, mock_config):
        """Test content formatting with large content that gets truncated."""
        view = MessagesView(mock_supabase, mock_config)

        # Create content that will exceed 10 lines when pretty-printed
        content = {
            f"key_{i}": {
                "nested_data": f"value_{i}",
                "more_data": {"sub_key": f"sub_value_{i}"},
            }
            for i in range(20)
        }

        result = view._format_content(content)

        assert isinstance(result, Text)
        assert "..." in result.plain  # Should be truncated

    def test_format_content_invalid_json(self, mock_supabase, mock_config):
        """Test content formatting with non-serializable content."""
        view = MessagesView(mock_supabase, mock_config)

        # Create content with non-serializable object
        class NonSerializable:
            def __str__(self):
                return "NonSerializable object"

        content = {"data": NonSerializable()}
        result = view._format_content(content)

        assert isinstance(result, Text)
        # Should fall back to string representation
        assert "NonSerializable" in result.plain or "data" in result.plain


class TestMessagesViewIntegration:
    """Test MessagesView integration with mocked dependencies."""

    def test_initialization(self, mock_supabase, mock_config):
        """Test MessagesView initialization."""
        view = MessagesView(mock_supabase, mock_config)

        assert view.supabase == mock_supabase
        assert view.config == mock_config
        assert view.messages_data == []
        assert view.current_task_id is None

    def test_data_assignment(self, mock_supabase, mock_config, sample_messages):
        """Test that message data can be assigned."""
        view = MessagesView(mock_supabase, mock_config)

        # Test data assignment
        view.messages_data = sample_messages
        assert len(view.messages_data) == 4

        # Test task ID assignment
        view.current_task_id = "task-123"
        assert view.current_task_id == "task-123"

        # Verify all messages are for the same task
        assert all(msg["task_id"] == "task-123" for msg in view.messages_data)

    def test_message_processing(self, mock_supabase, mock_config, sample_messages):
        """Test message data processing without UI dependencies."""
        view = MessagesView(mock_supabase, mock_config)

        for message in sample_messages:
            # Test timestamp formatting
            formatted_time = view._format_timestamp(message.get("created_at"))
            assert isinstance(formatted_time, str)
            assert formatted_time != "N/A"

            # Test content formatting
            formatted_content = view._format_content(message.get("content"))
            assert isinstance(formatted_content, Text)

            # Verify message structure
            assert "message_id" in message
            assert "source_agent_id" in message
            assert "target_agent_id" in message
            assert "message_type" in message
            assert "content" in message

    def test_message_types(self, mock_supabase, mock_config, sample_messages):
        """Test different message types in the sample data."""
        view = MessagesView(mock_supabase, mock_config)

        message_types = [msg["message_type"] for msg in sample_messages]
        assert "request" in message_types
        assert "delegation" in message_types
        assert "response" in message_types

        # Test formatting for each type
        for message in sample_messages:
            content = view._format_content(message["content"])
            msg_type = message["message_type"]

            if msg_type == "request":
                assert "task" in content.plain or "Analyze" in content.plain
            elif msg_type == "delegation":
                assert "task" in content.plain or "Fetch" in content.plain
            elif msg_type == "response":
                assert "status" in content.plain or "completed" in content.plain

    def test_chronological_order(self, mock_supabase, mock_config, sample_messages):
        """Test that messages maintain chronological order."""
        MessagesView(mock_supabase, mock_config)

        # Messages should be in chronological order (oldest first)
        timestamps = []
        for message in sample_messages:
            timestamp_str = message.get("created_at")
            if timestamp_str:
                dt = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
                timestamps.append(dt)

        # Verify chronological order
        for i in range(1, len(timestamps)):
            assert timestamps[i] >= timestamps[i - 1], (
                "Messages should be in chronological order"
            )

    def test_empty_messages(self, mock_supabase, mock_config):
        """Test handling of empty message list."""
        view = MessagesView(mock_supabase, mock_config)

        view.messages_data = []
        view.current_task_id = "task-456"

        # Should handle empty messages gracefully
        assert len(view.messages_data) == 0
        assert view.current_task_id == "task-456"

    def test_message_content_variations(self, mock_supabase, mock_config):
        """Test various content formats."""
        view = MessagesView(mock_supabase, mock_config)

        test_contents = [
            {},  # Empty
            None,  # None
            {"simple": "value"},  # Simple
            {"nested": {"key": "value"}},  # Nested
            {"list": [1, 2, 3]},  # With list
            {"mixed": {"str": "text", "num": 42, "bool": True}},  # Mixed types
        ]

        for content in test_contents:
            result = view._format_content(content)
            assert isinstance(result, Text)
            # Should not raise exceptions
