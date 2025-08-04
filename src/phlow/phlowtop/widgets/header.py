"""Header widget for phlowtop showing summary statistics."""

from typing import Any

from rich.text import Text
from textual.widgets import Static

from ..supabase_client import SupabaseMonitor


class PhlowTopHeader(Static):
    """Header widget displaying summary statistics."""

    DEFAULT_CSS = """
    PhlowTopHeader {
        dock: top;
        height: 3;
        background: $primary;
        color: $text;
        padding: 1;
    }
    """

    def __init__(self):
        """Initialize the header widget."""
        super().__init__()
        self.stats: dict[str, Any] = {
            "agents_online": 0,
            "agents_total": 0,
            "tasks_active": 0,
            "messages_per_minute": 0,
            "errors_last_hour": 0,
        }
        self.supabase_project = "unknown"
        self.is_realtime_connected = False

    def render(self) -> Text:
        """Render the header with current statistics."""
        # Top line: Title and project info
        title_line = Text()
        title_line.append("phlowtop v0.1.0", style="bold white")
        title_line.append(" - Supabase: ", style="white")
        title_line.append(self.supabase_project, style="cyan")

        # Realtime status indicator
        if self.is_realtime_connected:
            title_line.append("  [● REALTIME]", style="green")
        else:
            title_line.append("  [○ OFFLINE]", style="red")

        # Stats line
        stats_line = Text()
        stats_line.append("AGENTS: ", style="white")
        stats_line.append(
            f"{self.stats['agents_online']}/{self.stats['agents_total']} online",
            style="green" if self.stats["agents_online"] > 0 else "red",
        )

        stats_line.append("   TASKS: ", style="white")
        stats_line.append(
            f"{self.stats['tasks_active']} active",
            style="blue" if self.stats["tasks_active"] > 0 else "white",
        )

        stats_line.append("   MSG/MIN: ", style="white")
        stats_line.append(str(self.stats["messages_per_minute"]), style="cyan")

        stats_line.append("   ERRORS: ", style="white")
        stats_line.append(
            str(self.stats["errors_last_hour"]),
            style="red" if self.stats["errors_last_hour"] > 0 else "green",
        )

        # Combine lines with newline
        header_text = Text()
        header_text.append(title_line)
        header_text.append("\n")
        header_text.append(stats_line)

        return header_text

    async def update_stats(self, supabase_monitor: SupabaseMonitor) -> None:
        """Update statistics from Supabase monitor.

        Args:
            supabase_monitor: The Supabase monitor instance
        """
        try:
            self.stats = await supabase_monitor.get_summary_stats()
            self.is_realtime_connected = supabase_monitor.is_connected

            # Extract project name from URL
            if supabase_monitor.config.supabase_url:
                # Extract subdomain from URL like https://abc123.supabase.co
                url_parts = supabase_monitor.config.supabase_url.split("://")
                if len(url_parts) > 1:
                    domain_parts = url_parts[1].split(".")
                    if len(domain_parts) > 0:
                        self.supabase_project = domain_parts[0]

            # Trigger re-render
            self.refresh()

        except Exception:
            # If we can't get stats, show disconnected state
            self.is_realtime_connected = False
            self.refresh()
