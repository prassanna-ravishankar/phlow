"""Views for phlowtop TUI application."""

try:
    from .agents import AgentsView
    from .messages import MessagesView
    from .tasks import TasksView

    __all__ = ["AgentsView", "TasksView", "MessagesView"]
except ImportError:
    # Textual not available - this is expected when phlowtop extras not installed
    __all__ = ["AgentsView", "TasksView", "MessagesView"]
