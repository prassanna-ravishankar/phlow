# phlowtop: Implementation Guide

## Overview

phlowtop is a real-time terminal monitoring tool for phlow A2A agents, providing an htop-like interface to observe agent activity, task execution, and message flows.

## Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Phlow Agent   │───▶│    Supabase     │◀───│   phlowtop TUI  │
│   (Enhanced)    │    │   (Database +   │    │   (New Tool)    │
│                 │    │   Realtime)     │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

- **Phlow agents** write lifecycle events to Supabase
- **Supabase** stores data and provides real-time subscriptions
- **phlowtop** reads data and subscribes to updates for live monitoring

## Implementation Plan

### Phase 1: Database Schema Extensions

Add monitoring tables to track agent lifecycle and task execution:

```sql
-- Extend existing agent_cards table
ALTER TABLE agent_cards ADD COLUMN IF NOT EXISTS last_heartbeat TIMESTAMPTZ DEFAULT NOW();
ALTER TABLE agent_cards ADD COLUMN IF NOT EXISTS status TEXT DEFAULT 'IDLE'
    CHECK (status IN ('IDLE', 'WORKING', 'ERROR', 'OFFLINE'));
ALTER TABLE agent_cards ADD COLUMN IF NOT EXISTS active_tasks INTEGER DEFAULT 0;

-- New table for task tracking
CREATE TABLE IF NOT EXISTS phlow_tasks (
    task_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_id TEXT REFERENCES agent_cards(agent_id),
    client_agent_id TEXT,
    status TEXT DEFAULT 'SUBMITTED' CHECK (status IN ('SUBMITTED', 'WORKING', 'COMPLETED', 'FAILED')),
    task_type TEXT,
    error_message TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- New table for message flow tracking
CREATE TABLE IF NOT EXISTS phlow_messages (
    message_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    task_id UUID REFERENCES phlow_tasks(task_id) ON DELETE CASCADE,
    source_agent_id TEXT,
    target_agent_id TEXT,
    message_type TEXT, -- 'request', 'response', 'error'
    content JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for performance
CREATE INDEX idx_phlow_tasks_agent_id ON phlow_tasks(agent_id);
CREATE INDEX idx_phlow_tasks_status ON phlow_tasks(status);
CREATE INDEX idx_phlow_messages_task_id ON phlow_messages(task_id);

-- Enable Realtime
ALTER PUBLICATION supabase_realtime ADD TABLE agent_cards, phlow_tasks, phlow_messages;
```

### Phase 2: Enhance PhlowMiddleware

Add lifecycle logging methods to `src/phlow/middleware.py`:

```python
# New methods to add to PhlowMiddleware class

async def log_agent_heartbeat(self, agent_id: str) -> None:
    """Update agent heartbeat timestamp"""
    if self.supabase_client:
        await self.supabase_client.table('agent_cards').update({
            'last_heartbeat': 'now()',
            'status': 'IDLE'
        }).eq('agent_id', agent_id).execute()

async def log_task_received(self, task_id: str, agent_id: str, client_agent_id: str, task_type: str) -> None:
    """Log when a task is received"""
    if self.supabase_client:
        await self.supabase_client.table('phlow_tasks').insert({
            'task_id': task_id,
            'agent_id': agent_id,
            'client_agent_id': client_agent_id,
            'task_type': task_type,
            'status': 'SUBMITTED'
        }).execute()

        # Update agent status
        await self.supabase_client.table('agent_cards').update({
            'status': 'WORKING',
            'active_tasks': self.supabase_client.rpc('increment_active_tasks', {'agent_id': agent_id})
        }).eq('agent_id', agent_id).execute()

async def log_task_status(self, task_id: str, status: str, error_message: str = None) -> None:
    """Update task status"""
    if self.supabase_client:
        update_data = {'status': status, 'updated_at': 'now()'}
        if error_message:
            update_data['error_message'] = error_message

        await self.supabase_client.table('phlow_tasks').update(
            update_data
        ).eq('task_id', task_id).execute()

        # If completed/failed, decrement active tasks
        if status in ['COMPLETED', 'FAILED']:
            task = await self.supabase_client.table('phlow_tasks').select('agent_id').eq('task_id', task_id).single().execute()
            if task.data:
                await self.supabase_client.rpc('decrement_active_tasks', {'agent_id': task.data['agent_id']}).execute()

async def log_message(self, task_id: str, source_agent_id: str, target_agent_id: str, message_type: str, content: dict) -> None:
    """Log inter-agent messages"""
    if self.supabase_client:
        await self.supabase_client.table('phlow_messages').insert({
            'task_id': task_id,
            'source_agent_id': source_agent_id,
            'target_agent_id': target_agent_id,
            'message_type': message_type,
            'content': content
        }).execute()
```

Integration points in FastAPI:
- Call `log_agent_heartbeat` on startup and periodically via background task
- Call `log_task_received` when `/tasks/send` endpoint receives a request
- Call `log_task_status` when task completes or fails
- Call `log_message` for each A2A message exchange

### Phase 3: phlowtop TUI Application

Directory structure:
```
phlowtop/
├── pyproject.toml
├── src/
│   └── phlowtop/
│       ├── __init__.py
│       ├── __main__.py      # Entry point
│       ├── app.py           # Main Textual app
│       ├── config.py        # Configuration
│       ├── supabase.py      # Supabase client & subscriptions
│       ├── views/
│       │   ├── __init__.py
│       │   ├── agents.py    # Agents dashboard
│       │   ├── tasks.py     # Tasks view
│       │   └── messages.py  # Message log view
│       └── widgets/
│           ├── __init__.py
│           ├── header.py    # Summary stats header
│           └── footer.py    # Keybindings footer
└── tests/
```

Key dependencies in `pyproject.toml`:
```toml
[project]
name = "phlowtop"
version = "0.1.0"
dependencies = [
    "textual>=0.47.0",
    "supabase>=2.0.0",
    "python-dotenv>=1.0.0",
    "rich>=13.0.0",
]
```

### Phase 4: Core Implementation

#### 4.1 Main Application (`app.py`)

```python
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container
from textual.reactive import reactive

class PhlowTopApp(App):
    """Main phlowtop application"""

    BINDINGS = [
        Binding("1", "show_agents", "Agents"),
        Binding("2", "show_tasks", "Tasks"),
        Binding("3", "show_messages", "Messages"),
        Binding("q", "quit", "Quit"),
        Binding("f", "filter", "Filter"),
        Binding("s", "sort", "Sort"),
    ]

    current_view = reactive("agents")

    def compose(self) -> ComposeResult:
        yield Header()
        yield Container(id="main-content")
        yield Footer()

    async def on_mount(self) -> None:
        """Initialize Supabase connection and subscriptions"""
        await self.supabase.connect()
        await self.switch_view("agents")

    def action_show_agents(self) -> None:
        self.switch_view("agents")

    # ... other view switching methods
```

#### 4.2 Supabase Integration (`supabase.py`)

```python
from supabase import create_client, Client
from realtime import RealtimeClient
import asyncio

class SupabaseMonitor:
    """Handles Supabase connections and real-time subscriptions"""

    def __init__(self, url: str, key: str):
        self.client: Client = create_client(url, key)
        self.realtime: RealtimeClient = None
        self.callbacks = {}

    async def connect(self):
        """Initialize realtime connection"""
        self.realtime = self.client.realtime

    async def subscribe_agents(self, callback):
        """Subscribe to agent status changes"""
        channel = self.realtime.channel('agents')
        channel.on_postgres_changes(
            event='*',
            schema='public',
            table='agent_cards',
            callback=callback
        )
        await channel.subscribe()

    async def fetch_agents(self):
        """Get current agent statuses"""
        response = await self.client.table('agent_cards').select('*').execute()
        return response.data

    # Similar methods for tasks and messages
```

#### 4.3 Views Implementation

**Agents View** (`views/agents.py`):
```python
from textual.widgets import DataTable
from textual.reactive import reactive

class AgentsView(DataTable):
    """Display all agents with status and metrics"""

    def on_mount(self) -> None:
        self.add_columns(
            "Agent Name",
            "Status",
            "Active Tasks",
            "Uptime",
            "Endpoint",
            "Last Heartbeat"
        )

    async def update_agents(self, agents: list):
        """Update table with agent data"""
        self.clear()
        for agent in agents:
            status_style = self.get_status_style(agent['status'])
            self.add_row(
                agent['name'],
                Text(agent['status'], style=status_style),
                str(agent.get('active_tasks', 0)),
                self.calculate_uptime(agent['created_at']),
                agent['endpoint'],
                self.format_time(agent['last_heartbeat'])
            )
```

### Phase 5: Real-time Updates

Handle Supabase Realtime events:

```python
async def handle_agent_change(payload):
    """Process real-time agent updates"""
    event_type = payload['eventType']
    agent = payload['new'] if event_type != 'DELETE' else payload['old']

    if event_type == 'INSERT':
        await agents_view.add_agent(agent)
    elif event_type == 'UPDATE':
        await agents_view.update_agent(agent)
    elif event_type == 'DELETE':
        await agents_view.remove_agent(agent['agent_id'])
```

### Phase 6: Testing Strategy

1. **Unit Tests**: Test individual components (views, widgets, data formatting)
2. **Integration Tests**: Test Supabase connection and data flow
3. **Mock Real-time**: Use mock Supabase client for testing real-time updates
4. **E2E Tests**: Spin up test Supabase instance with Docker

## UI Layout

### Header
```
phlowtop v0.1.0 - Supabase: project-xyz
AGENTS: 12/15 online   TASKS: 34 active   MSG/S: 128   ERRORS: 3     [● REALTIME]
```

### Main Views

#### Agents Dashboard (View 1)
| AGENT NAME | STATUS | ACTIVE TASKS | UPTIME | ENDPOINT | LAST HEARTBEAT |
|------------|--------|--------------|--------|----------|----------------|
| FinanceBot | WORKING | 5 | 3h 45m | http://... | 10s ago |
| DataAgent | IDLE | 0 | 1d 2h | http://... | 5s ago |

#### Tasks View (View 2)
| TASK ID | STATUS | AGE | AGENT | CLIENT | MESSAGES |
|---------|--------|-----|-------|--------|----------|
| f47ac... | WORKING | 2m 10s | FinanceBot | UserAgent | 12 |

#### Message Log (View 3)
```
[Task: f47ac10b-58cc-4372-a567-0e02b2c3d479] - [Status: WORKING]
--------------------------------------------------------------------------------
[2025-08-04 22:50:10] UserAgent -> FinanceBot
    {
        "task": "Analyze GOOG stock performance for the last quarter."
    }
--------------------------------------------------------------------------------
[2025-08-04 22:50:12] FinanceBot -> DataAgent
    {
        "task": "Fetch historical stock data for GOOG, Q2 2025."
    }
```

### Footer
```
1 Agents  2 Tasks  3 Logs | F Filter | S Sort | Q Quit | ↑↓ Navigate | Enter Select
```

## Configuration

Environment variables (`.env`):
```bash
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_ANON_KEY=xxx
PHLOWTOP_REFRESH_RATE=1000  # ms
PHLOWTOP_MAX_MESSAGES=1000  # per task
```

## Future Enhancements

1. **Advanced Filtering**: Filter by agent skill, status, error type
2. **Performance Metrics**: Display CPU/Memory if agents report it
3. **Export Capabilities**: Save task logs, generate reports
4. **Agent Control**: Send signals to agents (pause, resume, shutdown)
5. **Distributed Mode**: Monitor multiple Supabase projects
6. **Alerts**: Configurable alerts for errors or SLA violations
