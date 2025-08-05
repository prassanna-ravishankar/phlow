"""Supabase client wrapper for phlowtop."""

import asyncio
from collections.abc import Callable
from datetime import datetime, timedelta
from typing import Any

from rich.console import Console
from supabase import Client, create_client

from .config import PhlowTopConfig


class SupabaseMonitor:
    """Handles Supabase connections and real-time subscriptions."""

    def __init__(self, config: PhlowTopConfig):
        """Initialize the Supabase monitor.

        Args:
            config: Application configuration
        """
        self.config = config
        self.client: Client | None = None
        self.console = Console()
        self.is_connected = False

        # Callback registry for real-time events
        self.callbacks: dict[str, list[Callable]] = {}

        # Real-time subscription state
        self.realtime_channel = None
        self.subscription_active = False

    async def connect(self) -> bool:
        """Connect to Supabase and initialize real-time subscriptions.

        Returns:
            True if connection successful, False otherwise
        """
        try:
            # Create Supabase client
            self.client = create_client(
                self.config.supabase_url, self.config.supabase_anon_key
            )

            # Test connection with a simple query
            await self._test_connection()

            self.is_connected = True
            self.console.print("[green]✓[/green] Connected to Supabase")
            return True

        except Exception as e:
            self.console.print(f"[red]✗[/red] Failed to connect to Supabase: {e}")
            return False

    async def _test_connection(self) -> None:
        """Test the Supabase connection."""
        if not self.client:
            raise ValueError("Client not initialized")

        # Try to fetch agent cards to test connection
        result = self.client.table("agent_cards").select("count").limit(1).execute()
        if not hasattr(result, "data"):
            raise ValueError("Invalid response from Supabase")

    async def fetch_agents(self) -> list[dict[str, Any]]:
        """Fetch all agents with their current status.

        Returns:
            List of agent data dictionaries
        """
        if not self.client:
            raise ValueError("Not connected to Supabase")

        try:
            result = self.client.table("agent_monitoring_summary").select("*").execute()
            return result.data or []
        except Exception as e:
            self.console.print(f"[red]Error fetching agents: {e}[/red]")
            return []

    async def fetch_tasks(self, agent_id: str | None = None) -> list[dict[str, Any]]:
        """Fetch tasks, optionally filtered by agent.

        Args:
            agent_id: Optional agent ID to filter by

        Returns:
            List of task data dictionaries
        """
        if not self.client:
            raise ValueError("Not connected to Supabase")

        try:
            query = (
                self.client.table("phlow_tasks")
                .select(
                    "task_id, agent_id, client_agent_id, status, task_type, "
                    "error_message, created_at, updated_at"
                )
                .order("created_at", desc=True)
                .limit(1000)
            )

            if agent_id:
                query = query.eq("agent_id", agent_id)

            result = query.execute()
            return result.data or []
        except Exception as e:
            self.console.print(f"[red]Error fetching tasks: {e}[/red]")
            return []

    async def fetch_messages(self, task_id: str) -> list[dict[str, Any]]:
        """Fetch messages for a specific task.

        Args:
            task_id: Task ID to fetch messages for

        Returns:
            List of message data dictionaries
        """
        if not self.client:
            raise ValueError("Not connected to Supabase")

        try:
            result = (
                self.client.table("phlow_messages")
                .select(
                    "message_id, task_id, source_agent_id, target_agent_id, "
                    "message_type, content, created_at"
                )
                .eq("task_id", task_id)
                .order("created_at", desc=False)
                .limit(self.config.max_messages_per_task)
                .execute()
            )

            return result.data or []
        except Exception as e:
            self.console.print(f"[red]Error fetching messages: {e}[/red]")
            return []

    async def get_summary_stats(self) -> dict[str, Any]:
        """Get summary statistics for the header.

        Returns:
            Dictionary with summary statistics
        """
        if not self.client:
            return {
                "agents_online": 0,
                "agents_total": 0,
                "tasks_active": 0,
                "messages_per_minute": 0,
                "errors_last_hour": 0,
            }

        try:
            # Get agent counts
            agents_result = (
                self.client.table("agent_cards")
                .select("agent_id, status, last_heartbeat")
                .execute()
            )

            agents_data = agents_result.data or []
            total_agents = len(agents_data)

            # Count online agents (heartbeat within last minute)
            cutoff_time = datetime.now() - timedelta(minutes=1)
            online_agents = sum(
                1
                for agent in agents_data
                if agent.get("last_heartbeat")
                and datetime.fromisoformat(
                    agent["last_heartbeat"].replace("Z", "+00:00")
                )
                > cutoff_time
            )

            # Get active tasks
            tasks_result = (
                self.client.table("phlow_tasks")
                .select("task_id")
                .in_("status", ["SUBMITTED", "WORKING"])
                .execute()
            )

            active_tasks = len(tasks_result.data or [])

            # Get recent messages for rate calculation
            recent_messages_result = (
                self.client.table("phlow_messages")
                .select("message_id")
                .gte("created_at", (datetime.now() - timedelta(minutes=1)).isoformat())
                .execute()
            )

            messages_per_minute = len(recent_messages_result.data or [])

            # Get recent errors
            errors_result = (
                self.client.table("phlow_tasks")
                .select("task_id")
                .eq("status", "FAILED")
                .gte("updated_at", (datetime.now() - timedelta(hours=1)).isoformat())
                .execute()
            )

            errors_last_hour = len(errors_result.data or [])

            return {
                "agents_online": online_agents,
                "agents_total": total_agents,
                "tasks_active": active_tasks,
                "messages_per_minute": messages_per_minute,
                "errors_last_hour": errors_last_hour,
            }

        except Exception as e:
            self.console.print(f"[red]Error fetching summary stats: {e}[/red]")
            return {
                "agents_online": 0,
                "agents_total": 0,
                "tasks_active": 0,
                "messages_per_minute": 0,
                "errors_last_hour": 0,
            }

    def register_callback(self, event_type: str, callback: Callable) -> None:
        """Register a callback for real-time events.

        Args:
            event_type: Type of event to listen for
            callback: Function to call when event occurs
        """
        if event_type not in self.callbacks:
            self.callbacks[event_type] = []
        self.callbacks[event_type].append(callback)

    async def start_realtime_subscriptions(self) -> None:
        """Start real-time subscriptions for live updates."""
        if not self.client or self.subscription_active:
            return

        try:
            # Create a realtime channel
            self.realtime_channel = self.client.realtime.channel("phlowtop")

            # Subscribe to agent_cards changes
            self.realtime_channel.on(
                "postgres_changes",
                {
                    "event": "*",
                    "schema": "public",
                    "table": "agent_cards",
                },
                self._handle_agent_change,
            )

            # Subscribe to phlow_tasks changes
            self.realtime_channel.on(
                "postgres_changes",
                {
                    "event": "*",
                    "schema": "public",
                    "table": "phlow_tasks",
                },
                self._handle_task_change,
            )

            # Subscribe to phlow_messages changes
            self.realtime_channel.on(
                "postgres_changes",
                {
                    "event": "*",
                    "schema": "public",
                    "table": "phlow_messages",
                },
                self._handle_message_change,
            )

            # Start the subscription
            await self.realtime_channel.subscribe()
            self.subscription_active = True

            self.console.print("[green]✓[/green] Real-time subscriptions started")

        except Exception as e:
            self.console.print(
                f"[red]Error starting real-time subscriptions: {e}[/red]"
            )

    def _handle_agent_change(self, payload: dict[str, Any]) -> None:
        """Handle real-time agent changes.

        Args:
            payload: Realtime payload from Supabase
        """
        try:
            payload.get("eventType", "")

            # Trigger registered callbacks
            for callback in self.callbacks.get("agent_change", []):
                try:
                    # Run callback in background to avoid blocking
                    asyncio.create_task(self._run_callback(callback, payload))
                except Exception as e:
                    self.console.print(f"[red]Error in agent callback: {e}[/red]")

        except Exception as e:
            self.console.print(f"[red]Error handling agent change: {e}[/red]")

    def _handle_task_change(self, payload: dict[str, Any]) -> None:
        """Handle real-time task changes.

        Args:
            payload: Realtime payload from Supabase
        """
        try:
            payload.get("eventType", "")

            # Trigger registered callbacks
            for callback in self.callbacks.get("task_change", []):
                try:
                    # Run callback in background to avoid blocking
                    asyncio.create_task(self._run_callback(callback, payload))
                except Exception as e:
                    self.console.print(f"[red]Error in task callback: {e}[/red]")

        except Exception as e:
            self.console.print(f"[red]Error handling task change: {e}[/red]")

    def _handle_message_change(self, payload: dict[str, Any]) -> None:
        """Handle real-time message changes.

        Args:
            payload: Realtime payload from Supabase
        """
        try:
            payload.get("eventType", "")

            # Trigger registered callbacks
            for callback in self.callbacks.get("message_change", []):
                try:
                    # Run callback in background to avoid blocking
                    asyncio.create_task(self._run_callback(callback, payload))
                except Exception as e:
                    self.console.print(f"[red]Error in message callback: {e}[/red]")

        except Exception as e:
            self.console.print(f"[red]Error handling message change: {e}[/red]")

    async def _run_callback(self, callback: Callable, payload: dict[str, Any]) -> None:
        """Run a callback function safely.

        Args:
            callback: Callback function to run
            payload: Payload to pass to callback
        """
        try:
            if asyncio.iscoroutinefunction(callback):
                await callback(payload)
            else:
                callback(payload)
        except Exception as e:
            self.console.print(f"[red]Error in callback: {e}[/red]")

    async def stop_realtime_subscriptions(self) -> None:
        """Stop real-time subscriptions."""
        if self.realtime_channel and self.subscription_active:
            try:
                await self.realtime_channel.unsubscribe()
                self.subscription_active = False
                self.console.print("[yellow]Real-time subscriptions stopped[/yellow]")
            except Exception as e:
                self.console.print(f"[red]Error stopping subscriptions: {e}[/red]")

    async def close(self) -> None:
        """Close the Supabase connection and cleanup."""
        # Stop realtime subscriptions first
        await self.stop_realtime_subscriptions()

        if self.client:
            # Close any open connections
            self.is_connected = False
            self.client = None
            self.console.print("[yellow]Disconnected from Supabase[/yellow]")
