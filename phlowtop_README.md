# phlowtop

Real-time terminal monitoring tool for phlow A2A agents, providing an htop-like interface to observe agent activity, task execution, and message flows.

## Installation

Install phlow with phlowtop support:

```bash
pip install phlow[phlowtop]
```

## Configuration

Configure phlowtop using environment variables or a `.env` file:

```bash
# Required: Supabase connection
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=your-anon-key

# Optional: UI settings
PHLOWTOP_REFRESH_RATE=1000          # Refresh rate in milliseconds (default: 1000)
PHLOWTOP_MAX_MESSAGES=1000          # Max messages per task (default: 1000)
PHLOWTOP_DATETIME_FORMAT="%Y-%m-%d %H:%M:%S"  # Timestamp format
PHLOWTOP_DEFAULT_VIEW=agents        # Default view: agents|tasks|messages
PHLOWTOP_CONNECTION_TIMEOUT=5000    # Connection timeout in ms
```

## Usage

Run phlowtop from the command line:

```bash
phlowtop
```

### Navigation

- **1** - Show Agents Dashboard (default view)
- **2** - Show Tasks View
- **3** - Show Messages View (requires task selection)
- **↑↓** - Navigate table rows
- **Enter** - Select item and drill down
- **Escape** - Go back to previous view
- **R** - Manually refresh data
- **F** - Filter (coming soon)
- **S** - Sort (coming soon)
- **Q** - Quit

### Views

#### 1. Agents Dashboard
Displays all registered agents with:
- Agent name and status (ONLINE/WORKING/IDLE/ERROR/OFFLINE)
- Active task count
- Uptime since last startup
- Service endpoint
- Last heartbeat timestamp

Select an agent with Enter to view its tasks.

#### 2. Tasks View
Shows tasks for all agents or filtered by selected agent:
- Task ID (truncated)
- Status (SUBMITTED/WORKING/COMPLETED/FAILED)
- Age since creation
- Agent and client names
- Task type
- Error message (if failed)

Select a task with Enter to view its message flow.

#### 3. Messages View
Chronological message flow for selected task:
- Timestamp of each message
- Source and target agent names
- Message type (request/response/error)
- JSON content (pretty-printed)

### Header Information

The header displays real-time summary statistics:
- **AGENTS**: Online/total agent counts
- **TASKS**: Active task count
- **MSG/MIN**: Messages per minute rate
- **ERRORS**: Failed tasks in last hour
- **REALTIME**: Connection status to Supabase

## Requirements

- Python 3.10+
- Supabase project with phlow schema
- Terminal with color support
- Network access to Supabase

## Features

- **Real-time monitoring** of agent activity
- **htop-like interface** with familiar navigation
- **Drill-down capability** from agents → tasks → messages
- **Auto-refresh** with configurable intervals
- **Color-coded status** indicators
- **Responsive layout** adapts to terminal size
- **Error handling** with graceful degradation

## Database Schema

phlowtop requires the phlow database schema with monitoring extensions. See the main phlow documentation for schema setup instructions.

## Troubleshooting

### Connection Issues
- Verify `SUPABASE_URL` and `SUPABASE_ANON_KEY` are correct
- Check network connectivity to Supabase
- Ensure Supabase project has the required tables

### No Data Showing
- Confirm agents are using phlow middleware with monitoring enabled
- Check that `enable_audit_log` is True in phlow configuration
- Verify agents are calling the lifecycle logging methods

### Performance Issues
- Increase `PHLOWTOP_REFRESH_RATE` to reduce update frequency
- Decrease `PHLOWTOP_MAX_MESSAGES` to limit message history
- Check terminal performance with large datasets

## Development

The phlowtop module is part of the main phlow package and can be extended with additional views and widgets using the Textual framework.
