"""Tests for PhlowMiddleware lifecycle logging methods."""

from unittest.mock import AsyncMock, Mock, patch
from uuid import uuid4

import pytest

from phlow.middleware import PhlowMiddleware
from phlow.types import AgentCard, PhlowConfig


@pytest.fixture
def mock_config():
    """Create a mock PhlowConfig for testing."""
    agent_card = AgentCard(
        name="Test Agent",
        description="Test agent for middleware lifecycle testing",
        service_url="http://localhost:8000",
        skills=["testing"],
        security_schemes={},
        metadata={"agent_id": "test-agent-1"},
    )

    config = Mock(spec=PhlowConfig)
    config.supabase_url = "https://test.supabase.co"
    config.supabase_anon_key = "test-key"
    config.enable_audit_log = True
    config.agent_card = agent_card
    config.private_key = "test-private-key"
    config.public_key = "test-public-key"

    # Mock rate limit configs
    rate_configs = Mock()
    rate_configs.auth_max_requests = 100
    rate_configs.auth_window_ms = 60000
    rate_configs.role_request_max_requests = 50
    rate_configs.role_request_window_ms = 60000
    config.rate_limit_configs = rate_configs

    return config


class TestMiddlewareLifecycleMethods:
    """Test PhlowMiddleware lifecycle logging methods."""

    @pytest.mark.asyncio
    async def test_log_agent_heartbeat_success(self, mock_config):
        """Test successful agent heartbeat logging."""
        with (
            patch("phlow.middleware.create_client") as mock_create_client,
            patch("phlow.middleware.get_key_store"),
            patch("phlow.middleware.KeyManager"),
            patch("phlow.middleware.httpx.AsyncClient"),
            patch("phlow.middleware.A2AClient"),
            patch("phlow.middleware.RoleCredentialVerifier"),
            patch("phlow.middleware.RoleCache"),
            patch("phlow.middleware.create_rate_limiter_from_env"),
            patch("phlow.middleware.structured_logger") as mock_logger,
        ):
            mock_supabase, mock_table = create_mock_supabase()
            mock_create_client.return_value = mock_supabase

            middleware = PhlowMiddleware(mock_config)
            middleware.supabase = mock_supabase

            agent_id = "test-agent-1"
            await middleware.log_agent_heartbeat(agent_id)

            # Verify table update was called correctly
            mock_table.update.assert_called_once_with(
                {"last_heartbeat": "now()", "status": "IDLE"}
            )
            mock_table.eq.assert_called_once_with("agent_id", agent_id)
            mock_table.execute.assert_called_once()

            # Verify structured logging
            mock_logger.log_event.assert_called_once_with(
                "agent_heartbeat",
                agent_id=agent_id,
                timestamp=mock_logger.log_event.call_args[1]["timestamp"],
            )

    @pytest.mark.asyncio
    async def test_log_agent_heartbeat_disabled(self, mock_config):
        """Test agent heartbeat logging when audit logging is disabled."""
        mock_config.enable_audit_log = False

        with (
            patch("phlow.middleware.create_client") as mock_create_client,
            patch("phlow.middleware.get_key_store"),
            patch("phlow.middleware.KeyManager"),
            patch("phlow.middleware.httpx.AsyncClient"),
            patch("phlow.middleware.A2AClient"),
            patch("phlow.middleware.RoleCredentialVerifier"),
            patch("phlow.middleware.RoleCache"),
            patch("phlow.middleware.create_rate_limiter_from_env"),
        ):
            mock_supabase, mock_table = create_mock_supabase()
            mock_create_client.return_value = mock_supabase

            middleware = PhlowMiddleware(mock_config)
            middleware.supabase = mock_supabase

            agent_id = "test-agent-1"
            await middleware.log_agent_heartbeat(agent_id)

            # Verify no database operations occurred
            mock_table.update.assert_not_called()
            mock_table.execute.assert_not_called()

    @pytest.mark.asyncio
    async def test_log_task_received_success(self, mock_config):
        """Test successful task received logging."""
        with (
            patch("phlow.middleware.create_client") as mock_create_client,
            patch("phlow.middleware.get_key_store"),
            patch("phlow.middleware.KeyManager"),
            patch("phlow.middleware.httpx.AsyncClient"),
            patch("phlow.middleware.A2AClient"),
            patch("phlow.middleware.RoleCredentialVerifier"),
            patch("phlow.middleware.RoleCache"),
            patch("phlow.middleware.create_rate_limiter_from_env"),
            patch("phlow.middleware.structured_logger") as mock_logger,
            patch("phlow.middleware.metrics_collector") as mock_metrics,
        ):
            mock_supabase, mock_table = create_mock_supabase()
            mock_create_client.return_value = mock_supabase

            middleware = PhlowMiddleware(mock_config)
            middleware.supabase = mock_supabase

            task_id = str(uuid4())
            agent_id = "test-agent-1"
            client_agent_id = "client-agent-1"
            task_type = "analysis"

            await middleware.log_task_received(
                task_id, agent_id, client_agent_id, task_type
            )

            # Verify task insertion
            expected_task_data = {
                "task_id": task_id,
                "agent_id": agent_id,
                "client_agent_id": client_agent_id,
                "task_type": task_type,
                "status": "SUBMITTED",
            }

            # Check that insert was called at least once with our task data
            insert_calls = [call[0][0] for call in mock_table.insert.call_args_list]
            assert expected_task_data in insert_calls

            # Verify agent status update
            expected_agent_update = {"status": "WORKING", "last_heartbeat": "now()"}
            update_calls = [call[0][0] for call in mock_table.update.call_args_list]
            assert expected_agent_update in update_calls

            # Verify RPC call for incrementing active tasks
            mock_supabase.rpc.assert_called_with(
                "increment_active_tasks", {"p_agent_id": agent_id}
            )

            # Verify structured logging
            mock_logger.log_event.assert_called_with(
                "task_received",
                task_id=task_id,
                agent_id=agent_id,
                client_agent_id=client_agent_id,
                task_type=task_type,
            )

            # Verify metrics
            mock_metrics.increment_counter.assert_called_with(
                "phlow_tasks_received_total",
                labels={"agent_id": agent_id, "task_type": task_type},
            )

    @pytest.mark.asyncio
    async def test_log_task_status_completion(self, mock_config):
        """Test task status update for completion."""
        with (
            patch("phlow.middleware.create_client") as mock_create_client,
            patch("phlow.middleware.get_key_store"),
            patch("phlow.middleware.KeyManager"),
            patch("phlow.middleware.httpx.AsyncClient"),
            patch("phlow.middleware.A2AClient"),
            patch("phlow.middleware.RoleCredentialVerifier"),
            patch("phlow.middleware.RoleCache"),
            patch("phlow.middleware.create_rate_limiter_from_env"),
            patch("phlow.middleware.structured_logger") as mock_logger,
            patch("phlow.middleware.metrics_collector") as mock_metrics,
        ):
            mock_supabase, mock_table = create_mock_supabase()
            # Mock the task query result
            mock_table.execute.return_value = Mock(data={"agent_id": "test-agent-1"})
            # Mock active tasks query result
            active_tasks_mock = AsyncMock()
            active_tasks_mock.execute.return_value = Mock(data={"active_tasks": 0})

            mock_create_client.return_value = mock_supabase

            middleware = PhlowMiddleware(mock_config)
            middleware.supabase = mock_supabase

            task_id = str(uuid4())
            status = "COMPLETED"

            await middleware.log_task_status(task_id, status)

            # Verify task status update
            expected_update_data = {"status": status, "updated_at": "now()"}
            update_calls = [call[0][0] for call in mock_table.update.call_args_list]
            assert expected_update_data in update_calls

            # Verify RPC call for decrementing active tasks
            mock_supabase.rpc.assert_called_with(
                "decrement_active_tasks", {"p_agent_id": "test-agent-1"}
            )

            # Verify structured logging
            mock_logger.log_event.assert_called_with(
                "task_status_updated",
                task_id=task_id,
                status=status,
                error_message=None,
            )

            # Verify metrics
            mock_metrics.increment_counter.assert_called_with(
                "phlow_task_status_changes_total", labels={"status": status}
            )

    @pytest.mark.asyncio
    async def test_log_task_status_failure_with_error(self, mock_config):
        """Test task status update for failure with error message."""
        with (
            patch("phlow.middleware.create_client") as mock_create_client,
            patch("phlow.middleware.get_key_store"),
            patch("phlow.middleware.KeyManager"),
            patch("phlow.middleware.httpx.AsyncClient"),
            patch("phlow.middleware.A2AClient"),
            patch("phlow.middleware.RoleCredentialVerifier"),
            patch("phlow.middleware.RoleCache"),
            patch("phlow.middleware.create_rate_limiter_from_env"),
            patch("phlow.middleware.structured_logger"),
        ):
            mock_supabase, mock_table = create_mock_supabase()
            # Mock the task query result
            mock_table.execute.return_value = Mock(data={"agent_id": "test-agent-1"})

            mock_create_client.return_value = mock_supabase

            middleware = PhlowMiddleware(mock_config)
            middleware.supabase = mock_supabase

            task_id = str(uuid4())
            status = "FAILED"
            error_message = "Connection timeout"

            await middleware.log_task_status(task_id, status, error_message)

            # Verify task status update includes error message
            expected_update_data = {
                "status": status,
                "updated_at": "now()",
                "error_message": error_message,
            }
            update_calls = [call[0][0] for call in mock_table.update.call_args_list]
            assert expected_update_data in update_calls

    @pytest.mark.asyncio
    async def test_log_message_success(self, mock_config):
        """Test successful message logging."""
        with (
            patch("phlow.middleware.create_client") as mock_create_client,
            patch("phlow.middleware.get_key_store"),
            patch("phlow.middleware.KeyManager"),
            patch("phlow.middleware.httpx.AsyncClient"),
            patch("phlow.middleware.A2AClient"),
            patch("phlow.middleware.RoleCredentialVerifier"),
            patch("phlow.middleware.RoleCache"),
            patch("phlow.middleware.create_rate_limiter_from_env"),
            patch("phlow.middleware.structured_logger") as mock_logger,
            patch("phlow.middleware.metrics_collector") as mock_metrics,
        ):
            mock_supabase, mock_table = create_mock_supabase()
            mock_create_client.return_value = mock_supabase

            middleware = PhlowMiddleware(mock_config)
            middleware.supabase = mock_supabase

            task_id = str(uuid4())
            source_agent_id = "agent-1"
            target_agent_id = "agent-2"
            message_type = "request"
            content = {"action": "process", "data": "test-data"}

            await middleware.log_message(
                task_id, source_agent_id, target_agent_id, message_type, content
            )

            # Verify message insertion
            expected_message_data = {
                "task_id": task_id,
                "source_agent_id": source_agent_id,
                "target_agent_id": target_agent_id,
                "message_type": message_type,
                "content": content,
            }
            mock_table.insert.assert_called_with(expected_message_data)

            # Verify structured logging
            mock_logger.log_event.assert_called_with(
                "message_logged",
                task_id=task_id,
                source_agent_id=source_agent_id,
                target_agent_id=target_agent_id,
                message_type=message_type,
            )

            # Verify metrics
            mock_metrics.increment_counter.assert_called_with(
                "phlow_messages_total",
                labels={
                    "source_agent": source_agent_id,
                    "target_agent": target_agent_id,
                    "message_type": message_type,
                },
            )

    @pytest.mark.asyncio
    async def test_error_handling_in_lifecycle_methods(self, mock_config):
        """Test error handling in lifecycle methods."""
        with (
            patch("phlow.middleware.create_client") as mock_create_client,
            patch("phlow.middleware.get_key_store"),
            patch("phlow.middleware.KeyManager"),
            patch("phlow.middleware.httpx.AsyncClient"),
            patch("phlow.middleware.A2AClient"),
            patch("phlow.middleware.RoleCredentialVerifier"),
            patch("phlow.middleware.RoleCache"),
            patch("phlow.middleware.create_rate_limiter_from_env"),
            patch("phlow.middleware.structured_logger") as mock_logger,
        ):
            mock_supabase, mock_table = create_mock_supabase()
            # Make the execute method raise an exception
            mock_table.execute.side_effect = Exception("Database error")

            mock_create_client.return_value = mock_supabase

            middleware = PhlowMiddleware(mock_config)
            middleware.supabase = mock_supabase

            # Test heartbeat error handling
            await middleware.log_agent_heartbeat("test-agent-1")
            mock_logger.log_event.assert_called_with(
                "agent_heartbeat_failed",
                agent_id="test-agent-1",
                error="Database error",
            )

            # Reset mock
            mock_logger.reset_mock()

            # Test task received error handling
            await middleware.log_task_received(
                str(uuid4()), "test-agent-1", "client-agent-1", "test"
            )
            mock_logger.log_event.assert_called_with(
                "task_received_failed",
                task_id=mock_logger.log_event.call_args[1]["task_id"],
                agent_id="test-agent-1",
                error="Database error",
            )

            # Reset mock
            mock_logger.reset_mock()

            # Test task status error handling
            task_id = str(uuid4())
            await middleware.log_task_status(task_id, "COMPLETED")
            mock_logger.log_event.assert_called_with(
                "task_status_update_failed",
                task_id=task_id,
                status="COMPLETED",
                error="Database error",
            )

            # Reset mock
            mock_logger.reset_mock()

            # Test message logging error handling
            task_id = str(uuid4())
            await middleware.log_message(
                task_id, "agent-1", "agent-2", "request", {"test": "data"}
            )
            mock_logger.log_event.assert_called_with(
                "message_logging_failed",
                task_id=task_id,
                source_agent_id="agent-1",
                target_agent_id="agent-2",
                error="Database error",
            )


def create_mock_supabase():
    """Helper function to create consistent mock supabase setup."""
    client = Mock()

    # Mock table operations - synchronous methods that return the table for chaining
    mock_table = Mock()
    mock_table.update = Mock(return_value=mock_table)
    mock_table.insert = Mock(return_value=mock_table)
    mock_table.select = Mock(return_value=mock_table)
    mock_table.eq = Mock(return_value=mock_table)
    mock_table.single = Mock(return_value=mock_table)

    # execute should be async and return a result
    async def mock_execute():
        return Mock(data={"agent_id": "test-agent-1"})

    mock_table.execute = AsyncMock(side_effect=mock_execute)

    client.table = Mock(return_value=mock_table)

    # RPC should be a mock that returns a result with execute method
    mock_rpc_result = Mock()
    mock_rpc_result.execute = AsyncMock(return_value=Mock(data=5))
    client.rpc = Mock(return_value=mock_rpc_result)

    return client, mock_table
