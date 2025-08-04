"""Agents dashboard view for phlowtop."""

from typing import Any

from rich.text import Text
from textual.widgets import DataTable

from ..config import PhlowTopConfig
from ..supabase_client import SupabaseMonitor


class AgentsView(DataTable):
    """Display all agents with status and metrics."""

    DEFAULT_CSS = """
    AgentsView {
        dock: fill;
    }
    """

    def __init__(self, supabase_monitor: SupabaseMonitor, config: PhlowTopConfig):
        """Initialize the agents view.

        Args:
            supabase_monitor: Supabase monitor instance
            config: Application configuration
        """
        super().__init__()
        self.supabase = supabase_monitor
        self.config = config
        self.agents_data: list[dict[str, Any]] = []

        # Configure table
        self.cursor_type = "row"
        self.zebra_stripes = True

    async def on_mount(self) -> None:
        """Initialize the table columns."""
        self.add_columns(
            "Agent Name",
            "Status",
            "Active Tasks",
            "Uptime",
            "Endpoint",
            "Last Heartbeat",
        )

        await self.refresh_data()

    async def refresh_data(self) -> None:
        """Refresh agents data from Supabase."""
        try:
            self.agents_data = await self.supabase.fetch_agents()
            await self._update_table()
        except Exception as e:
            # Handle error gracefully
            self.app.notify(f"Error refreshing agents: {e}", severity="error")

    async def _update_table(self) -> None:
        """Update the table with current agents data."""
        # Clear existing rows
        self.clear()
        self.add_columns(
            "Agent Name",
            "Status",
            "Active Tasks",
            "Uptime",
            "Endpoint",
            "Last Heartbeat",
        )

        for agent in self.agents_data:
            # Format status with color
            status = agent.get("status", "UNKNOWN")
            status_text = self._format_status(status)

            # Format other fields
            name = agent.get("name", "Unknown")
            active_tasks = str(agent.get("active_tasks", 0))
            endpoint = agent.get("service_url", "N/A")

            # Calculate uptime and format heartbeat
            uptime = self._calculate_uptime(agent.get("created_at"))
            heartbeat = self._format_heartbeat(agent.get("last_heartbeat"))

            self.add_row(name, status_text, active_tasks, uptime, endpoint, heartbeat)

    def _format_status(self, status: str) -> Text:
        """Format status with appropriate color.

        Args:
            status: Agent status string

        Returns:
            Rich Text object with colored status
        """
        color_map = {
            "ONLINE": "green",
            "WORKING": "blue",
            "IDLE": "white",
            "ERROR": "red",
            "OFFLINE": "gray",
        }

        color = color_map.get(status, "white")
        return Text(status, style=color)

    def _calculate_uptime(self, created_at: str | None) -> str:
        """Calculate uptime from creation timestamp.

        Args:
            created_at: ISO timestamp string

        Returns:
            Formatted uptime string
        """
        if not created_at:
            return "N/A"

        try:
            from datetime import datetime

            created = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
            now = datetime.now(tz=created.tzinfo)
            delta = now - created

            days = delta.days
            hours, remainder = divmod(delta.seconds, 3600)
            minutes, _ = divmod(remainder, 60)

            if days > 0:
                return f"{days}d {hours}h"
            elif hours > 0:
                return f"{hours}h {minutes}m"
            else:
                return f"{minutes}m"

        except Exception:
            return "N/A"

    def _format_heartbeat(self, last_heartbeat: str | None) -> str:
        """Format last heartbeat timestamp.

        Args:
            last_heartbeat: ISO timestamp string

        Returns:
            Formatted time string
        """
        if not last_heartbeat:
            return "Never"

        try:
            from datetime import datetime

            heartbeat = datetime.fromisoformat(last_heartbeat.replace("Z", "+00:00"))
            now = datetime.now(tz=heartbeat.tzinfo)
            delta = now - heartbeat

            total_seconds = int(delta.total_seconds())

            if total_seconds < 60:
                return f"{total_seconds}s ago"
            elif total_seconds < 3600:
                minutes = total_seconds // 60
                return f"{minutes}m ago"
            elif total_seconds < 86400:
                hours = total_seconds // 3600
                return f"{hours}h ago"
            else:
                days = total_seconds // 86400
                return f"{days}d ago"

        except Exception:
            return "N/A"

    async def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        """Handle row selection - drill down to tasks for selected agent."""
        if event.row_key.value is not None and self.agents_data:
            row_index = event.row_key.value
            if 0 <= row_index < len(self.agents_data):
                agent = self.agents_data[row_index]
                agent_id = agent.get("agent_id")
                if agent_id:
                    # Notify parent app of agent selection
                    await self.app.on_agent_selected(agent_id)
