"""Tests for audit logging module."""

from unittest.mock import MagicMock

import pytest

from phlow.audit import AuditLogger, create_audit_entry


class TestCreateAuditEntry:
    def test_creates_basic_entry(self):
        entry = create_audit_entry("auth_success", "agent-1")
        assert entry.event == "auth_success"
        assert entry.agent_id == "agent-1"
        assert entry.target_agent_id is None
        assert entry.details is None
        assert entry.timestamp  # non-empty

    def test_creates_full_entry(self):
        entry = create_audit_entry(
            "message_sent",
            "agent-1",
            target_agent_id="agent-2",
            details={"message_id": "m123"},
        )
        assert entry.target_agent_id == "agent-2"
        assert entry.details == {"message_id": "m123"}


class TestAuditLogger:
    def _make_supabase_mock(self, success=True):
        mock = MagicMock()
        execute_result = MagicMock()
        execute_result.data = [{"id": 1}] if success else None
        mock.table.return_value.insert.return_value.execute.return_value = (
            execute_result
        )
        return mock

    def test_queues_entries(self):
        supabase = self._make_supabase_mock()
        logger = AuditLogger(supabase)
        entry = create_audit_entry("test", "agent-1")
        # log_sync should add to queue without flushing (below batch size)
        logger.log_sync(entry)
        assert len(logger.queue) == 1

    def test_flushes_at_batch_size(self):
        supabase = self._make_supabase_mock()
        logger = AuditLogger(supabase)
        logger.max_batch_size = 2

        logger.log_sync(create_audit_entry("e1", "a1"))
        assert len(logger.queue) == 1

        logger.log_sync(create_audit_entry("e2", "a2"))
        # Should have flushed
        assert len(logger.queue) == 0
        supabase.table.assert_called_with("auth_audit_log")

    @pytest.mark.asyncio
    async def test_async_flush(self):
        supabase = self._make_supabase_mock()
        logger = AuditLogger(supabase)
        entry = create_audit_entry("test", "agent-1")
        logger.queue.append(entry)

        await logger.flush()
        assert len(logger.queue) == 0
        supabase.table.assert_called_with("auth_audit_log")

    @pytest.mark.asyncio
    async def test_flush_empty_queue_is_noop(self):
        supabase = self._make_supabase_mock()
        logger = AuditLogger(supabase)
        await logger.flush()
        supabase.table.assert_not_called()

    @pytest.mark.asyncio
    async def test_requeues_on_failure(self):
        supabase = self._make_supabase_mock(success=False)
        logger = AuditLogger(supabase)
        entry = create_audit_entry("test", "agent-1")
        logger.queue.append(entry)

        await logger.flush()
        # Should re-add on failure
        assert len(logger.queue) == 1

    @pytest.mark.asyncio
    async def test_requeues_on_exception(self):
        supabase = MagicMock()
        supabase.table.return_value.insert.return_value.execute.side_effect = Exception(
            "db error"
        )
        logger = AuditLogger(supabase)
        entry = create_audit_entry("test", "agent-1")
        logger.queue.append(entry)

        await logger.flush()
        assert len(logger.queue) == 1

    def test_sync_flush(self):
        supabase = self._make_supabase_mock()
        logger = AuditLogger(supabase)
        logger.max_batch_size = 1
        logger.log_sync(create_audit_entry("e1", "a1"))
        supabase.table.assert_called_with("auth_audit_log")

    @pytest.mark.asyncio
    async def test_async_log(self):
        supabase = self._make_supabase_mock()
        logger = AuditLogger(supabase)
        entry = create_audit_entry("test", "agent-1")
        await logger.log(entry)
        assert len(logger.queue) == 1

    @pytest.mark.asyncio
    async def test_async_log_flushes_at_batch_size(self):
        supabase = self._make_supabase_mock()
        logger = AuditLogger(supabase)
        logger.max_batch_size = 2

        await logger.log(create_audit_entry("e1", "a1"))
        assert len(logger.queue) == 1

        await logger.log(create_audit_entry("e2", "a2"))
        assert len(logger.queue) == 0

    def test_sync_flush_requeues_on_failure(self):
        supabase = self._make_supabase_mock(success=False)
        logger = AuditLogger(supabase)
        logger.max_batch_size = 1
        logger.log_sync(create_audit_entry("e1", "a1"))
        assert len(logger.queue) == 1

    def test_sync_flush_requeues_on_exception(self):
        supabase = MagicMock()
        supabase.table.return_value.insert.return_value.execute.side_effect = Exception(
            "db error"
        )
        logger = AuditLogger(supabase)
        logger.max_batch_size = 1
        logger.log_sync(create_audit_entry("e1", "a1"))
        assert len(logger.queue) == 1

    @pytest.mark.asyncio
    async def test_start_stop_background_flush(self):
        import asyncio

        supabase = self._make_supabase_mock()
        logger = AuditLogger(supabase, flush_interval_seconds=0.05)
        logger.queue.append(create_audit_entry("e1", "a1"))

        await logger.start_background_flush()
        assert logger._running is True

        # Starting again is idempotent
        await logger.start_background_flush()

        await asyncio.sleep(0.1)

        await logger.stop_background_flush()
        assert logger._running is False
