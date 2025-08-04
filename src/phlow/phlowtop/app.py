"""Main phlowtop Textual application."""

import asyncio

from rich.console import Console
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container
from textual.reactive import reactive
from textual.widgets import Footer, LoadingIndicator

from .config import PhlowTopConfig
from .supabase_client import SupabaseMonitor
from .views.agents import AgentsView
from .views.messages import MessagesView
from .views.tasks import TasksView
from .widgets.header import PhlowTopHeader


class PhlowTopApp(App):
    """Main phlowtop application."""

    CSS = """
    Screen {
        background: $background;
    }

    .header {
        dock: top;
        height: 3;
        background: $primary;
        color: $text;
    }

    .main-content {
        dock: fill;
        background: $surface;
    }

    .loading {
        dock: fill;
        align: center middle;
    }

    .error {
        color: $error;
        text-align: center;
        margin: 1;
    }
    """

    BINDINGS = [
        Binding("1", "show_agents", "Agents", priority=True),
        Binding("2", "show_tasks", "Tasks", priority=True),
        Binding("3", "show_messages", "Messages", priority=True),
        Binding("q", "quit", "Quit", priority=True),
        Binding("f", "filter", "Filter"),
        Binding("s", "sort", "Sort"),
        Binding("r", "refresh", "Refresh"),
        Binding("escape", "go_back", "Back"),
    ]

    TITLE = "phlowtop - Real-time Agent Monitor"

    # Reactive state
    current_view = reactive("agents")
    selected_agent_id: str | None = reactive(None)
    selected_task_id: str | None = reactive(None)
    is_connected = reactive(False)
    error_message: str | None = reactive(None)

    def __init__(self):
        """Initialize the application."""
        super().__init__()
        self.console = Console()

        # Load configuration
        try:
            self.config = PhlowTopConfig.from_env()
            self.config.validate_required_fields()
        except Exception as e:
            self.error_message = f"Configuration error: {e}"
            self.config = None
            return

        # Initialize Supabase monitor
        self.supabase = SupabaseMonitor(self.config)

        # Views
        self.agents_view: AgentsView | None = None
        self.tasks_view: TasksView | None = None
        self.messages_view: MessagesView | None = None
        self.header: PhlowTopHeader | None = None

        # Auto-refresh timer
        self.refresh_timer: asyncio.Task | None = None

    def compose(self) -> ComposeResult:
        """Compose the UI layout."""
        if self.error_message:
            yield Container(f"Error: {self.error_message}", classes="error")
            yield Footer()
            return

        # Header with summary stats
        self.header = PhlowTopHeader()
        yield self.header

        if not self.is_connected:
            yield Container(
                LoadingIndicator(), "Connecting to Supabase...", classes="loading"
            )
        else:
            # Main content area
            with Container(classes="main-content", id="main-content"):
                # Views will be mounted here dynamically
                pass

        yield Footer()

    async def on_mount(self) -> None:
        """Initialize the application after mounting."""
        if self.error_message:
            return

        # Connect to Supabase
        try:
            connected = await self.supabase.connect()
            if not connected:
                self.error_message = "Failed to connect to Supabase"
                await self.recompose()
                return

            self.is_connected = True

            # Start real-time subscriptions
            await self.supabase.start_realtime_subscriptions()

            # Initialize views
            await self._initialize_views()

            # Show default view
            await self.action_show_agents()

            # Start auto-refresh timer
            self._start_refresh_timer()

        except Exception as e:
            self.error_message = f"Initialization error: {e}"
            await self.recompose()

    async def _initialize_views(self) -> None:
        """Initialize all views."""
        self.agents_view = AgentsView(self.supabase, self.config)
        self.tasks_view = TasksView(self.supabase, self.config)
        self.messages_view = MessagesView(self.supabase, self.config)

    def _start_refresh_timer(self) -> None:
        """Start the auto-refresh timer."""
        if self.refresh_timer:
            self.refresh_timer.cancel()

        self.refresh_timer = asyncio.create_task(self._refresh_loop())

    async def _refresh_loop(self) -> None:
        """Auto-refresh loop for updating data."""
        while True:
            try:
                await asyncio.sleep(self.config.refresh_rate_ms / 1000.0)
                await self._refresh_current_view()

                # Update header stats
                if self.header:
                    await self.header.update_stats(self.supabase)

            except asyncio.CancelledError:
                break
            except Exception as e:
                self.console.print(f"[red]Refresh error: {e}[/red]")

    async def _refresh_current_view(self) -> None:
        """Refresh the currently active view."""
        if self.current_view == "agents" and self.agents_view:
            await self.agents_view.refresh_data()
        elif self.current_view == "tasks" and self.tasks_view:
            await self.tasks_view.refresh_data(self.selected_agent_id)
        elif self.current_view == "messages" and self.messages_view:
            if self.selected_task_id:
                await self.messages_view.refresh_data(self.selected_task_id)

    async def _switch_view(self, view_name: str) -> None:
        """Switch to a different view."""
        if not self.is_connected:
            return

        # Remove current view
        main_container = self.query_one("#main-content", Container)
        main_container.remove_children()

        # Mount new view
        if view_name == "agents" and self.agents_view:
            await main_container.mount(self.agents_view)
            await self.agents_view.refresh_data()
        elif view_name == "tasks" and self.tasks_view:
            await main_container.mount(self.tasks_view)
            await self.tasks_view.refresh_data(self.selected_agent_id)
        elif view_name == "messages" and self.messages_view:
            await main_container.mount(self.messages_view)
            if self.selected_task_id:
                await self.messages_view.refresh_data(self.selected_task_id)

        self.current_view = view_name

    # Action handlers
    async def action_show_agents(self) -> None:
        """Show agents dashboard."""
        await self._switch_view("agents")

    async def action_show_tasks(self) -> None:
        """Show tasks view."""
        await self._switch_view("tasks")

    async def action_show_messages(self) -> None:
        """Show messages view."""
        if self.selected_task_id:
            await self._switch_view("messages")
        else:
            self.notify("No task selected. Select a task first.", severity="warning")

    async def action_refresh(self) -> None:
        """Manually refresh current view."""
        await self._refresh_current_view()
        if self.header:
            await self.header.update_stats(self.supabase)
        self.notify("Refreshed", timeout=1)

    async def action_filter(self) -> None:
        """Show filter dialog."""
        # TODO: Implement filtering
        self.notify("Filtering not implemented yet", severity="info")

    async def action_sort(self) -> None:
        """Show sort dialog."""
        # TODO: Implement sorting
        self.notify("Sorting not implemented yet", severity="info")

    async def action_go_back(self) -> None:
        """Go back to previous view."""
        if self.current_view == "messages":
            await self.action_show_tasks()
        elif self.current_view == "tasks" and self.selected_agent_id:
            self.selected_agent_id = None
            await self.action_show_agents()

    async def on_agent_selected(self, agent_id: str) -> None:
        """Handle agent selection from agents view."""
        self.selected_agent_id = agent_id
        await self.action_show_tasks()

    async def on_task_selected(self, task_id: str) -> None:
        """Handle task selection from tasks view."""
        self.selected_task_id = task_id
        await self.action_show_messages()

    async def on_unmount(self) -> None:
        """Cleanup when app is closing."""
        if self.refresh_timer:
            self.refresh_timer.cancel()

        if self.supabase:
            await self.supabase.close()
