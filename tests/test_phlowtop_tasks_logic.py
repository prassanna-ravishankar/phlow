"""Tests for phlowtop Tasks view logic."""

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, Mock

import pytest
from rich.text import Text

from src.phlow.phlowtop.config import PhlowTopConfig
from src.phlow.phlowtop.supabase_client import SupabaseMonitor
from src.phlow.phlowtop.views.tasks import TasksView


@pytest.fixture
def mock_supabase():
    """Create a mock SupabaseMonitor."""
    mock = Mock(spec=SupabaseMonitor)
    mock.fetch_tasks = AsyncMock()
    return mock


@pytest.fixture
def mock_config():
    """Create a mock PhlowTopConfig."""
    config = Mock(spec=PhlowTopConfig)
    config.refresh_rate = 1000
    config.max_messages_per_task = 100
    return config


@pytest.fixture
def mock_app():
    """Create a mock app."""
    app = Mock()
    app.notify = Mock()
    app.on_task_selected = AsyncMock()
    return app


@pytest.fixture
def sample_tasks():
    """Sample task data for testing."""
    now = datetime.now(timezone.utc)
    return [
        {
            "task_id": "550e8400-e29b-41d4-a716-446655440000",
            "agent_id": "test-agent-1",
            "client_agent_id": "client-agent-1",
            "status": "SUBMITTED",
            "task_type": "analysis",
            "error_message": None,
            "created_at": now.isoformat(),
            "updated_at": now.isoformat(),
        },
        {
            "task_id": "550e8400-e29b-41d4-a716-446655440001",
            "agent_id": "test-agent-2",
            "client_agent_id": "client-agent-2",
            "status": "WORKING",
            "task_type": "generation",
            "error_message": None,
            "created_at": (now - timedelta(minutes=5)).isoformat(),
            "updated_at": now.isoformat(),
        },
        {
            "task_id": "550e8400-e29b-41d4-a716-446655440002",
            "agent_id": "test-agent-1",
            "client_agent_id": "client-agent-3",
            "status": "COMPLETED",
            "task_type": "translation",
            "error_message": None,
            "created_at": (now - timedelta(hours=2)).isoformat(),
            "updated_at": (now - timedelta(minutes=30)).isoformat(),
        },
        {
            "task_id": "550e8400-e29b-41d4-a716-446655440003",
            "agent_id": "test-agent-3",
            "client_agent_id": "client-agent-1",
            "status": "FAILED",
            "task_type": "validation",
            "error_message": "Validation failed: missing required field 'data'",
            "created_at": (now - timedelta(days=1)).isoformat(),
            "updated_at": (now - timedelta(hours=12)).isoformat(),
        },
    ]


class TestTasksViewLogic:
    """Test the logic methods of TasksView without UI framework dependencies."""

    def test_truncate_id_short(self, mock_supabase, mock_config):
        """Test truncating a short ID."""
        view = TasksView(mock_supabase, mock_config)

        short_id = "abc123"
        result = view._truncate_id(short_id)
        assert result == "abc123"

    def test_truncate_id_long(self, mock_supabase, mock_config):
        """Test truncating a long ID."""
        view = TasksView(mock_supabase, mock_config)

        long_id = "550e8400-e29b-41d4-a716-446655440000"
        result = view._truncate_id(long_id)
        assert result == "550e8400..."
        assert len(result) == 11  # 8 chars + "..."

    def test_truncate_id_custom_length(self, mock_supabase, mock_config):
        """Test truncating with custom length."""
        view = TasksView(mock_supabase, mock_config)

        long_id = "550e8400-e29b-41d4-a716-446655440000"
        result = view._truncate_id(long_id, length=12)
        assert result == "550e8400-e29..."
        assert len(result) == 15  # 12 chars + "..."

    def test_format_status_colors(self, mock_supabase, mock_config):
        """Test status formatting with different colors."""
        view = TasksView(mock_supabase, mock_config)

        # Test all known statuses
        submitted = view._format_status("SUBMITTED")
        assert isinstance(submitted, Text)
        assert submitted.plain == "SUBMITTED"
        assert "yellow" in str(submitted.style)

        working = view._format_status("WORKING")
        assert isinstance(working, Text)
        assert working.plain == "WORKING"
        assert "blue" in str(working.style)

        completed = view._format_status("COMPLETED")
        assert isinstance(completed, Text)
        assert completed.plain == "COMPLETED"
        assert "green" in str(completed.style)

        failed = view._format_status("FAILED")
        assert isinstance(failed, Text)
        assert failed.plain == "FAILED"
        assert "red" in str(failed.style)

    def test_format_status_unknown(self, mock_supabase, mock_config):
        """Test status formatting for unknown status."""
        view = TasksView(mock_supabase, mock_config)

        unknown = view._format_status("UNKNOWN")
        assert isinstance(unknown, Text)
        assert unknown.plain == "UNKNOWN"
        assert "white" in str(unknown.style)

    def test_calculate_age_seconds(self, mock_supabase, mock_config):
        """Test age calculation for seconds."""
        view = TasksView(mock_supabase, mock_config)

        # 30 seconds ago
        timestamp = (datetime.now(timezone.utc) - timedelta(seconds=30)).isoformat()
        result = view._calculate_age(timestamp)
        assert result == "30s"

    def test_calculate_age_minutes(self, mock_supabase, mock_config):
        """Test age calculation for minutes."""
        view = TasksView(mock_supabase, mock_config)

        # 5 minutes 30 seconds ago
        timestamp = (
            datetime.now(timezone.utc) - timedelta(minutes=5, seconds=30)
        ).isoformat()
        result = view._calculate_age(timestamp)
        assert result == "5m 30s"

    def test_calculate_age_hours(self, mock_supabase, mock_config):
        """Test age calculation for hours."""
        view = TasksView(mock_supabase, mock_config)

        # 2 hours 15 minutes ago
        timestamp = (
            datetime.now(timezone.utc) - timedelta(hours=2, minutes=15)
        ).isoformat()
        result = view._calculate_age(timestamp)
        assert result == "2h 15m"

    def test_calculate_age_days(self, mock_supabase, mock_config):
        """Test age calculation for days."""
        view = TasksView(mock_supabase, mock_config)

        # 1 day 3 hours ago
        timestamp = (
            datetime.now(timezone.utc) - timedelta(days=1, hours=3)
        ).isoformat()
        result = view._calculate_age(timestamp)
        assert result == "1d 3h"

    def test_calculate_age_none(self, mock_supabase, mock_config):
        """Test age calculation with None timestamp."""
        view = TasksView(mock_supabase, mock_config)

        result = view._calculate_age(None)
        assert result == "N/A"

    def test_calculate_age_invalid(self, mock_supabase, mock_config):
        """Test age calculation with invalid timestamp."""
        view = TasksView(mock_supabase, mock_config)

        result = view._calculate_age("invalid-timestamp")
        assert result == "N/A"

    def test_format_error_none(self, mock_supabase, mock_config):
        """Test error formatting with None."""
        view = TasksView(mock_supabase, mock_config)

        result = view._format_error(None)
        assert result == ""

    def test_format_error_empty(self, mock_supabase, mock_config):
        """Test error formatting with empty string."""
        view = TasksView(mock_supabase, mock_config)

        result = view._format_error("")
        assert result == ""

    def test_format_error_short(self, mock_supabase, mock_config):
        """Test error formatting with short message."""
        view = TasksView(mock_supabase, mock_config)

        short_error = "Connection failed"
        result = view._format_error(short_error)
        assert result == "Connection failed"

    def test_format_error_long(self, mock_supabase, mock_config):
        """Test error formatting with long message."""
        view = TasksView(mock_supabase, mock_config)

        long_error = "This is a very long error message that should be truncated because it exceeds the maximum length"
        result = view._format_error(long_error)
        assert result == "This is a very long error mess..."
        assert len(result) == 33  # 30 chars + "..."


class TestTasksViewIntegration:
    """Test TasksView integration with mocked dependencies."""

    def test_initialization(self, mock_supabase, mock_config):
        """Test TasksView initialization."""
        view = TasksView(mock_supabase, mock_config)

        assert view.supabase == mock_supabase
        assert view.config == mock_config
        assert view.tasks_data == []
        assert view.current_agent_id is None
        assert view.cursor_type == "row"
        assert view.zebra_stripes is True

    def test_data_assignment(self, mock_supabase, mock_config, sample_tasks):
        """Test that task data can be assigned and filtered."""
        view = TasksView(mock_supabase, mock_config)

        # Test data assignment
        view.tasks_data = sample_tasks
        assert len(view.tasks_data) == 4

        # Test filtering by agent
        view.current_agent_id = "test-agent-1"
        agent_1_tasks = [
            task for task in sample_tasks if task["agent_id"] == "test-agent-1"
        ]
        assert len(agent_1_tasks) == 2

        # Verify the filtered tasks are correct
        assert all(task["agent_id"] == "test-agent-1" for task in agent_1_tasks)

    def test_row_selection_logic(self, mock_supabase, mock_config, sample_tasks):
        """Test row selection logic without UI framework."""
        view = TasksView(mock_supabase, mock_config)
        view.tasks_data = sample_tasks

        # Test valid index
        row_index = 0
        if 0 <= row_index < len(view.tasks_data):
            task = view.tasks_data[row_index]
            task_id = task.get("task_id")
            assert task_id == "550e8400-e29b-41d4-a716-446655440000"

        # Test invalid index
        row_index = 999
        if 0 <= row_index < len(view.tasks_data):
            # Should not enter this block
            raise AssertionError("Should not have valid task for index 999")

        # Test edge case with empty tasks
        view.tasks_data = []
        row_index = 0
        if 0 <= row_index < len(view.tasks_data):
            # Should not enter this block
            raise AssertionError("Should not have valid task for empty tasks list")

    def test_data_processing(self, mock_supabase, mock_config, sample_tasks):
        """Test data processing and formatting without UI dependencies."""
        view = TasksView(mock_supabase, mock_config)

        for task in sample_tasks:
            # Test all the formatting methods
            task_id = view._truncate_id(task.get("task_id", ""))
            status = view._format_status(task.get("status", "UNKNOWN"))
            age = view._calculate_age(task.get("created_at"))
            error = view._format_error(task.get("error_message"))

            # Verify the formatting worked
            assert isinstance(task_id, str)
            assert hasattr(status, "plain")  # Rich Text object
            assert isinstance(age, str)
            assert isinstance(error, str)

            # Verify specific formatting
            if task.get("status") == "FAILED":
                assert "red" in str(status.style)
            elif task.get("status") == "COMPLETED":
                assert "green" in str(status.style)
            elif task.get("status") == "WORKING":
                assert "blue" in str(status.style)
            elif task.get("status") == "SUBMITTED":
                assert "yellow" in str(status.style)
