"""Messages view for phlowtop."""

import json
from typing import Any

from rich.text import Text
from textual.containers import ScrollableContainer
from textual.widgets import Static

from ..config import PhlowTopConfig
from ..supabase_client import SupabaseMonitor


class MessagesView(ScrollableContainer):
    """Display chronological message flow for a selected task."""

    DEFAULT_CSS = """
    MessagesView {
        dock: fill;
        background: $surface;
    }

    .message-item {
        margin: 1 0;
        padding: 1;
        border: solid $primary;
    }

    .message-header {
        background: $primary;
        color: $text;
        padding: 0 1;
    }

    .message-content {
        padding: 1;
        background: $panel;
    }
    """

    def __init__(self, supabase_monitor: SupabaseMonitor, config: PhlowTopConfig):
        """Initialize the messages view.

        Args:
            supabase_monitor: Supabase monitor instance
            config: Application configuration
        """
        super().__init__()
        self.supabase = supabase_monitor
        self.config = config
        self.messages_data: list[dict[str, Any]] = []
        self.current_task_id: str | None = None

    async def refresh_data(self, task_id: str) -> None:
        """Refresh messages data for a specific task.

        Args:
            task_id: Task ID to fetch messages for
        """
        try:
            self.current_task_id = task_id
            self.messages_data = await self.supabase.fetch_messages(task_id)
            await self._update_messages()
        except Exception as e:
            self.app.notify(f"Error refreshing messages: {e}", severity="error")

    async def _update_messages(self) -> None:
        """Update the message display with current data."""
        # Clear existing content
        await self.remove_children()

        if not self.messages_data:
            await self.mount(
                Static(
                    Text("No messages found for this task.", style="dim"),
                    classes="message-item",
                )
            )
            return

        # Add task header
        task_header = Static(
            f"Task: {self.current_task_id} - Messages: {len(self.messages_data)}",
            classes="message-header",
        )
        await self.mount(task_header)

        # Add each message
        for i, message in enumerate(self.messages_data):
            await self._add_message_item(message, i)

    async def _add_message_item(self, message: dict[str, Any], index: int) -> None:
        """Add a single message item to the display.

        Args:
            message: Message data dictionary
            index: Message index for numbering
        """
        # Format timestamp
        timestamp = self._format_timestamp(message.get("created_at"))

        # Get message details
        source = message.get("source_agent_id", "Unknown")
        target = message.get("target_agent_id", "Unknown")
        msg_type = message.get("message_type", "unknown")
        content = message.get("content", {})

        # Create header text
        header_text = Text()
        header_text.append(f"[{timestamp}] ", style="cyan")
        header_text.append(f"{source}", style="green")
        header_text.append(" -> ", style="white")
        header_text.append(f"{target}", style="blue")
        header_text.append(f" ({msg_type})", style="yellow")

        # Format content
        content_text = self._format_content(content)

        # Create message widget
        message_widget = Static(
            Text.assemble(header_text, "\n", content_text), classes="message-item"
        )

        await self.mount(message_widget)

    def _format_timestamp(self, timestamp: str | None) -> str:
        """Format timestamp for display.

        Args:
            timestamp: ISO timestamp string

        Returns:
            Formatted timestamp string
        """
        if not timestamp:
            return "N/A"

        try:
            from datetime import datetime

            dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
            return dt.strftime(self.config.datetime_format)
        except Exception:
            return timestamp

    def _format_content(self, content: dict[str, Any]) -> Text:
        """Format message content for display.

        Args:
            content: Message content dictionary

        Returns:
            Formatted Rich Text
        """
        if not content:
            return Text("(empty)", style="dim")

        try:
            # Pretty print JSON content
            formatted_json = json.dumps(content, indent=2, ensure_ascii=False)

            # Truncate if too long
            max_lines = 10
            lines = formatted_json.split("\n")
            if len(lines) > max_lines:
                lines = lines[:max_lines] + ["    ..."]
                formatted_json = "\n".join(lines)

            return Text(formatted_json, style="white")

        except Exception:
            # Fallback to string representation
            return Text(str(content), style="white")
