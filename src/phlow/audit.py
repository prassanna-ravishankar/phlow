"""Audit logging for Phlow authentication."""

import asyncio
import logging
from datetime import datetime
from typing import Any, List, Optional

from .types import AuditLog

logger = logging.getLogger(__name__)


class AuditLogger:
    """Audit logger for Phlow authentication events."""

    def __init__(self, supabase_client: Any, flush_interval_seconds: int = 5):
        """Initialize audit logger.

        Args:
            supabase_client: Supabase client instance
            flush_interval_seconds: How often to flush logs to database
        """
        self.supabase = supabase_client
        self.flush_interval = flush_interval_seconds
        self.queue: List[AuditLog] = []
        self.max_batch_size = 100
        self._flush_task: Optional[asyncio.Task] = None
        self._running = False

    async def log(self, entry: AuditLog) -> None:
        """Add an audit log entry to the queue.

        Args:
            entry: The audit log entry to add
        """
        self.queue.append(entry)

        if len(self.queue) >= self.max_batch_size:
            await self.flush()

    def log_sync(self, entry: AuditLog) -> None:
        """Add an audit log entry synchronously.

        Args:
            entry: The audit log entry to add
        """
        self.queue.append(entry)

        if len(self.queue) >= self.max_batch_size:
            self._flush_sync()

    async def flush(self) -> None:
        """Flush all queued audit logs to the database."""
        if not self.queue:
            return

        entries = self.queue[: self.max_batch_size]
        self.queue = self.queue[self.max_batch_size :]

        try:
            # Convert entries to database format
            db_entries = []
            for entry in entries:
                db_entry = {
                    "timestamp": entry.timestamp,
                    "event": entry.event,
                    "agent_id": entry.agent_id,
                    "target_agent_id": entry.target_agent_id,
                    "details": entry.details or {},
                }
                db_entries.append(db_entry)

            # Insert into Supabase
            result = (
                self.supabase.table("phlow_audit_logs").insert(db_entries).execute()
            )

            if result.data is None:
                logger.error(f"Failed to insert audit logs: {result}")
                # Re-add entries to queue for retry
                self.queue = entries + self.queue

        except Exception as e:
            logger.error(f"Error flushing audit logs: {e}")
            # Re-add entries to queue for retry
            self.queue = entries + self.queue

    def _flush_sync(self) -> None:
        """Flush audit logs synchronously."""
        if not self.queue:
            return

        entries = self.queue[: self.max_batch_size]
        self.queue = self.queue[self.max_batch_size :]

        try:
            # Convert entries to database format
            db_entries = []
            for entry in entries:
                db_entry = {
                    "timestamp": entry.timestamp,
                    "event": entry.event,
                    "agent_id": entry.agent_id,
                    "target_agent_id": entry.target_agent_id,
                    "details": entry.details or {},
                }
                db_entries.append(db_entry)

            # Insert into Supabase
            result = (
                self.supabase.table("phlow_audit_logs").insert(db_entries).execute()
            )

            if result.data is None:
                logger.error(f"Failed to insert audit logs: {result}")
                # Re-add entries to queue for retry
                self.queue = entries + self.queue

        except Exception as e:
            logger.error(f"Error flushing audit logs: {e}")
            # Re-add entries to queue for retry
            self.queue = entries + self.queue

    async def start_background_flush(self) -> None:
        """Start background task for periodic flushing."""
        if self._running:
            return

        self._running = True
        self._flush_task = asyncio.create_task(self._flush_loop())

    async def stop_background_flush(self) -> None:
        """Stop background flushing and flush remaining logs."""
        self._running = False

        if self._flush_task:
            self._flush_task.cancel()
            try:
                await self._flush_task
            except asyncio.CancelledError:
                pass

        # Flush any remaining logs
        await self.flush()

    async def _flush_loop(self) -> None:
        """Background loop for periodic flushing."""
        while self._running:
            try:
                await asyncio.sleep(self.flush_interval)
                await self.flush()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in audit flush loop: {e}")


def create_audit_entry(
    event: str,
    agent_id: str,
    target_agent_id: Optional[str] = None,
    details: Optional[dict] = None,
) -> AuditLog:
    """Create an audit log entry.

    Args:
        event: The event type
        agent_id: The agent ID that triggered the event
        target_agent_id: The target agent ID (optional)
        details: Additional event details (optional)

    Returns:
        The audit log entry
    """
    return AuditLog(
        timestamp=datetime.utcnow().isoformat(),
        event=event,
        agent_id=agent_id,
        target_agent_id=target_agent_id,
        details=details,
    )
