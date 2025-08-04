"""Tasks view for phlowtop."""

from typing import Any

from rich.text import Text
from textual.widgets import DataTable

from ..config import PhlowTopConfig
from ..supabase_client import SupabaseMonitor


class TasksView(DataTable):
    """Display tasks with filtering and sorting capabilities."""

    DEFAULT_CSS = """
    TasksView {
        dock: fill;
    }
    """

    def __init__(self, supabase_monitor: SupabaseMonitor, config: PhlowTopConfig):
        """Initialize the tasks view.

        Args:
            supabase_monitor: Supabase monitor instance
            config: Application configuration
        """
        super().__init__()
        self.supabase = supabase_monitor
        self.config = config
        self.tasks_data: list[dict[str, Any]] = []
        self.current_agent_id: str | None = None

        # Configure table
        self.cursor_type = "row"
        self.zebra_stripes = True

    async def on_mount(self) -> None:
        """Initialize the table columns."""
        self.add_columns("Task ID", "Status", "Age", "Agent", "Client", "Type", "Error")

    async def refresh_data(self, agent_id: str | None = None) -> None:
        """Refresh tasks data from Supabase.

        Args:
            agent_id: Optional agent ID to filter by
        """
        try:
            self.current_agent_id = agent_id
            self.tasks_data = await self.supabase.fetch_tasks(agent_id)
            await self._update_table()
        except Exception as e:
            self.app.notify(f"Error refreshing tasks: {e}", severity="error")

    async def _update_table(self) -> None:
        """Update the table with current tasks data."""
        # Clear existing rows
        self.clear()

        # Add title showing filter status
        title = "Tasks"
        if self.current_agent_id:
            title += f" (filtered by agent: {self.current_agent_id})"

        self.add_columns("Task ID", "Status", "Age", "Agent", "Client", "Type", "Error")

        for task in self.tasks_data:
            # Format task data
            task_id = self._truncate_id(task.get("task_id", ""))
            status = self._format_status(task.get("status", "UNKNOWN"))
            age = self._calculate_age(task.get("created_at"))
            agent = task.get("agent_id", "N/A")
            client = task.get("client_agent_id", "N/A")
            task_type = task.get("task_type", "N/A")
            error = self._format_error(task.get("error_message"))

            self.add_row(task_id, status, age, agent, client, task_type, error)

    def _truncate_id(self, task_id: str, length: int = 8) -> str:
        """Truncate task ID for display.

        Args:
            task_id: Full task ID
            length: Number of characters to show

        Returns:
            Truncated ID
        """
        if len(task_id) <= length:
            return task_id
        return task_id[:length] + "..."

    def _format_status(self, status: str) -> Text:
        """Format status with appropriate color.

        Args:
            status: Task status string

        Returns:
            Rich Text object with colored status
        """
        color_map = {
            "SUBMITTED": "yellow",
            "WORKING": "blue",
            "COMPLETED": "green",
            "FAILED": "red",
        }

        color = color_map.get(status, "white")
        return Text(status, style=color)

    def _calculate_age(self, created_at: str | None) -> str:
        """Calculate task age from creation timestamp.

        Args:
            created_at: ISO timestamp string

        Returns:
            Formatted age string
        """
        if not created_at:
            return "N/A"

        try:
            from datetime import datetime

            created = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
            now = datetime.now(tz=created.tzinfo)
            delta = now - created

            total_seconds = int(delta.total_seconds())

            if total_seconds < 60:
                return f"{total_seconds}s"
            elif total_seconds < 3600:
                minutes = total_seconds // 60
                return f"{minutes}m {total_seconds % 60}s"
            elif total_seconds < 86400:
                hours = total_seconds // 3600
                minutes = (total_seconds % 3600) // 60
                return f"{hours}h {minutes}m"
            else:
                days = total_seconds // 86400
                hours = (total_seconds % 86400) // 3600
                return f"{days}d {hours}h"

        except Exception:
            return "N/A"

    def _format_error(self, error_message: str | None) -> str:
        """Format error message for display.

        Args:
            error_message: Error message string

        Returns:
            Formatted error string
        """
        if not error_message:
            return ""

        # Truncate long error messages
        max_length = 30
        if len(error_message) > max_length:
            return error_message[:max_length] + "..."

        return error_message

    async def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        """Handle row selection - drill down to messages for selected task."""
        if event.row_key.value is not None and self.tasks_data:
            row_index = event.row_key.value
            if 0 <= row_index < len(self.tasks_data):
                task = self.tasks_data[row_index]
                task_id = task.get("task_id")
                if task_id:
                    # Notify parent app of task selection
                    await self.app.on_task_selected(task_id)
