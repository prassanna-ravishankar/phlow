# Installation

## Python Package

Phlow is a pure Python framework. Choose your preferred package manager:

### UV (Recommended)
```bash
# Add to existing project
uv add phlow

# Or create new project with phlow
uv init my-agent && cd my-agent
uv add phlow
```

### Pip
```bash
pip install phlow
```

### Poetry
```bash
poetry add phlow
```

### Requirements File
```txt
phlow>=0.1.0
fastapi>=0.100.0          # For FastAPI integration
uvicorn[standard]>=0.23.0  # ASGI server
```

## System Requirements

- **Python**: 3.10 or higher
- **Docker**: Required for E2E testing
- **Optional**: UV package manager for better performance

## Development Setup

If you're contributing to Phlow or running the examples:

```bash
# Clone repository
git clone https://github.com/prassanna-ravishankar/phlow.git
cd phlow

# Install with development dependencies
uv sync --dev

# See available development tasks
uv run task --list
```

## Docker Setup

For E2E testing and multi-agent development:

### Docker Desktop
```bash
# Install Docker Desktop from docker.com
# Phlow auto-detects standard Docker setup
```

### Rancher Desktop (macOS/Linux)
```bash
# Install Rancher Desktop
# Phlow auto-detects Rancher Desktop socket at ~/.rd/docker.sock
```

## Supabase Setup

Phlow requires a Supabase project for agent registry and audit logs.

### 1. Create Supabase Project
- Go to [supabase.com](https://supabase.com)
- Create a new project
- Note your project URL and anon key

### 2. Set up Database Schema
Run the SQL from `docs/database-schema.sql` in your Supabase SQL editor:

```sql
-- Copy and run the contents of docs/database-schema.sql
-- This creates agent_cards table and RLS policies
```

### 3. Environment Variables
```bash
# Required for Phlow
export SUPABASE_URL="https://your-project.supabase.co"
export SUPABASE_ANON_KEY="your-anon-key"

# Required for A2A authentication
export PRIVATE_KEY="your-rsa-private-key"
export PUBLIC_KEY="your-rsa-public-key"

# Optional for AI features
export GEMINI_API_KEY="your-gemini-api-key"
```

## Testing Installation

```bash
# Test Phlow imports
python -c "from phlow import AgentCard, PhlowConfig; print('✅ Phlow installed')"

# Test development setup (if you cloned repo)
uv run task test-unit

# Test E2E setup (requires Docker)
uv run task test-e2e
```

## IDE Setup

### VS Code
Recommended extensions:
- Python
- Pylance (type checking)
- Ruff (linting/formatting)

### PyCharm
- Enable type checking
- Configure Ruff as external tool

## Troubleshooting

### Import Errors
```bash
# Ensure you're in the right environment
which python
pip list | grep phlow
```

### Docker Issues
```bash
# Test Docker accessibility
docker run hello-world

# For Rancher Desktop users
export DOCKER_HOST=unix://$HOME/.rd/docker.sock
```

### Supabase Connection
```bash
# Test Supabase connection
curl -H "apikey: YOUR_ANON_KEY" "https://your-project.supabase.co/rest/v1/agent_cards"
```

## Next Steps

- [Quick Start](quickstart.md) - Build your first agent
- [Configuration](configuration.md) - Learn all options
- [A2A Compatibility](a2a-compatibility.md) - Protocol compliance
