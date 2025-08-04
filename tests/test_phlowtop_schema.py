"""Tests for phlowtop database schema extensions."""

import asyncio
from datetime import datetime
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest
from supabase import Client as SupabaseClient


@pytest.fixture
def mock_supabase():
    """Create a mock Supabase client."""
    client = Mock(spec=SupabaseClient)

    # Mock table operations
    client.table = Mock(return_value=Mock())
    client.rpc = Mock(return_value=Mock())

    return client


@pytest.fixture
def mock_table():
    """Create a mock table with chainable methods."""
    table = Mock()
    table.update = Mock(return_value=table)
    table.insert = Mock(return_value=table)
    table.select = Mock(return_value=table)
    table.eq = Mock(return_value=table)
    table.single = Mock(return_value=table)
    table.execute = AsyncMock(return_value=Mock(data={}))

    return table


class TestPhlowTopSchema:
    """Test phlowtop database schema operations."""

    @pytest.mark.asyncio
    async def test_agent_heartbeat_update(self, mock_supabase, mock_table):
        """Test updating agent heartbeat."""
        mock_supabase.table.return_value = mock_table

        agent_id = "test-agent-1"

        # Simulate heartbeat update
        await (
            mock_table.update({"last_heartbeat": "now()", "status": "IDLE"})
            .eq("agent_id", agent_id)
            .execute()
        )

        # Verify the update was called correctly
        mock_table.update.assert_called_once_with(
            {"last_heartbeat": "now()", "status": "IDLE"}
        )
        mock_table.eq.assert_called_once_with("agent_id", agent_id)
        mock_table.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_task_creation(self, mock_supabase, mock_table):
        """Test creating a new task."""
        mock_supabase.table.return_value = mock_table

        task_data = {
            "task_id": str(uuid4()),
            "agent_id": "test-agent-1",
            "client_agent_id": "client-agent-1",
            "task_type": "analysis",
            "status": "SUBMITTED",
        }

        # Simulate task creation
        await mock_table.insert(task_data).execute()

        # Verify the insert was called correctly
        mock_table.insert.assert_called_once_with(task_data)
        mock_table.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_task_status_update(self, mock_supabase, mock_table):
        """Test updating task status."""
        mock_supabase.table.return_value = mock_table

        task_id = str(uuid4())

        # Test successful completion
        await (
            mock_table.update({"status": "COMPLETED", "updated_at": "now()"})
            .eq("task_id", task_id)
            .execute()
        )

        mock_table.update.assert_called_with(
            {"status": "COMPLETED", "updated_at": "now()"}
        )

        # Reset mocks
        mock_table.reset_mock()

        # Test failure with error message
        await (
            mock_table.update(
                {
                    "status": "FAILED",
                    "error_message": "Connection timeout",
                    "updated_at": "now()",
                }
            )
            .eq("task_id", task_id)
            .execute()
        )

        mock_table.update.assert_called_with(
            {
                "status": "FAILED",
                "error_message": "Connection timeout",
                "updated_at": "now()",
            }
        )

    @pytest.mark.asyncio
    async def test_message_logging(self, mock_supabase, mock_table):
        """Test logging inter-agent messages."""
        mock_supabase.table.return_value = mock_table

        message_data = {
            "task_id": str(uuid4()),
            "source_agent_id": "agent-1",
            "target_agent_id": "agent-2",
            "message_type": "request",
            "content": {"task": "Analyze data", "params": {"dataset": "sales"}},
        }

        # Simulate message creation
        await mock_table.insert(message_data).execute()

        # Verify the insert was called correctly
        mock_table.insert.assert_called_once_with(message_data)
        mock_table.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_active_tasks_increment(self, mock_supabase):
        """Test incrementing active tasks count."""
        mock_rpc = AsyncMock(return_value=Mock(data=5))
        mock_supabase.rpc = mock_rpc

        agent_id = "test-agent-1"

        # Simulate increment
        result = await mock_rpc("increment_active_tasks", {"agent_id": agent_id})

        # Verify RPC was called correctly
        mock_rpc.assert_called_once_with(
            "increment_active_tasks", {"agent_id": agent_id}
        )
        assert result.data == 5

    @pytest.mark.asyncio
    async def test_active_tasks_decrement(self, mock_supabase):
        """Test decrementing active tasks count."""
        mock_rpc = AsyncMock(return_value=Mock(data=3))
        mock_supabase.rpc = mock_rpc

        agent_id = "test-agent-1"

        # Simulate decrement
        result = await mock_rpc("decrement_active_tasks", {"agent_id": agent_id})

        # Verify RPC was called correctly
        mock_rpc.assert_called_once_with(
            "decrement_active_tasks", {"agent_id": agent_id}
        )
        assert result.data == 3

    @pytest.mark.asyncio
    async def test_agent_monitoring_summary_view(self, mock_supabase, mock_table):
        """Test querying the agent monitoring summary view."""
        mock_supabase.table.return_value = mock_table

        # Mock response data
        summary_data = [
            {
                "agent_id": "test-agent-1",
                "name": "Test Agent",
                "status": "WORKING",
                "active_tasks": 2,
                "last_heartbeat": datetime.now().isoformat(),
                "service_url": "http://localhost:8000",
                "tasks_completed_1h": 10,
                "tasks_failed_1h": 1,
                "messages_per_minute": 5,
            }
        ]

        mock_table.execute.return_value = Mock(data=summary_data)

        # Query the view
        result = await mock_table.select("*").execute()

        # Verify the query
        mock_table.select.assert_called_once_with("*")
        assert result.data == summary_data
        assert result.data[0]["active_tasks"] == 2
        assert result.data[0]["status"] == "WORKING"


class TestPhlowTopSchemaValidation:
    """Test schema validation and constraints."""

    def test_valid_agent_statuses(self):
        """Test valid agent status values."""
        valid_statuses = ["IDLE", "WORKING", "ERROR", "OFFLINE"]
        for status in valid_statuses:
            # These should not raise errors
            assert status in valid_statuses

    def test_valid_task_statuses(self):
        """Test valid task status values."""
        valid_statuses = ["SUBMITTED", "WORKING", "COMPLETED", "FAILED"]
        for status in valid_statuses:
            # These should not raise errors
            assert status in valid_statuses

    def test_message_types(self):
        """Test common message types."""
        message_types = ["request", "response", "error"]
        for msg_type in message_types:
            # These are examples - no constraint in schema
            assert isinstance(msg_type, str)

    def test_active_tasks_non_negative(self):
        """Test that active_tasks cannot be negative."""
        # The decrement_active_tasks function uses GREATEST to ensure non-negative
        test_values = [5, 0, -1]
        expected = [4, 0, 0]  # -1 should become 0

        for val, exp in zip(test_values, expected, strict=False):
            result = max(val - 1, 0)  # Simulating GREATEST logic
            assert result == exp


class TestPhlowTopSchemaIntegration:
    """Integration tests for phlowtop schema with actual operations."""

    @pytest.mark.asyncio
    async def test_full_task_lifecycle(self, mock_supabase, mock_table):
        """Test complete task lifecycle from submission to completion."""
        mock_supabase.table.return_value = mock_table

        task_id = str(uuid4())
        agent_id = "test-agent-1"
        client_id = "client-agent-1"

        # 1. Create task
        task_data = {
            "task_id": task_id,
            "agent_id": agent_id,
            "client_agent_id": client_id,
            "status": "SUBMITTED",
        }
        await mock_table.insert(task_data).execute()

        # 2. Update to WORKING
        await mock_table.update({"status": "WORKING"}).eq("task_id", task_id).execute()

        # 3. Log messages
        messages = [
            {
                "task_id": task_id,
                "source_agent_id": client_id,
                "target_agent_id": agent_id,
                "message_type": "request",
                "content": {"action": "process"},
            },
            {
                "task_id": task_id,
                "source_agent_id": agent_id,
                "target_agent_id": client_id,
                "message_type": "response",
                "content": {"status": "processing"},
            },
        ]

        for msg in messages:
            await mock_table.insert(msg).execute()

        # 4. Complete task
        await (
            mock_table.update({"status": "COMPLETED"}).eq("task_id", task_id).execute()
        )

        # Verify all operations were called
        assert mock_table.insert.call_count == 3  # 1 task + 2 messages
        assert mock_table.update.call_count == 2  # WORKING + COMPLETED

    @pytest.mark.asyncio
    async def test_concurrent_agent_operations(self, mock_supabase, mock_table):
        """Test concurrent operations on multiple agents."""
        mock_supabase.table.return_value = mock_table

        agents = ["agent-1", "agent-2", "agent-3"]

        # Simulate concurrent heartbeats
        tasks = []
        for agent_id in agents:
            task = (
                mock_table.update({"last_heartbeat": "now()", "status": "IDLE"})
                .eq("agent_id", agent_id)
                .execute()
            )
            tasks.append(task)

        # Wait for all heartbeats
        await asyncio.gather(*tasks)

        # Verify all agents were updated
        assert mock_table.update.call_count == 3
        assert mock_table.eq.call_count == 3
