# Phlow Auth Python

JWT authentication middleware for AI agents with Supabase integration.

## Installation

```bash
pip install phlow-auth
```

## Quick Start

```python
from phlow_auth import PhlowMiddleware, PhlowConfig, AgentCard

# Configure your agent
config = PhlowConfig(
    supabase_url="https://your-project.supabase.co",
    supabase_anon_key="your-anon-key",
    agent_card=AgentCard(
        name="My Agent",
        description="AI assistant agent",
        service_url="https://my-agent.com",
        skills=["chat", "analysis"],
        metadata={"agent_id": "my-agent-id", "public_key": "your-public-key"}
    ),
    private_key="your-private-key"
)

# Initialize middleware
phlow = PhlowMiddleware(config)

# Use as decorator with FastAPI
from fastapi import FastAPI, Request

app = FastAPI()

@app.post("/api/chat")
@phlow.authenticate()
async def chat(request: Request):
    # Access agent context
    agent = request.phlow.agent
    supabase = request.phlow.supabase
    return {"message": f"Hello from {agent.name}"}
```

## Features

- **JWT Authentication** - Verify A2A Protocol JWT tokens
- **Agent Storage** - Store and retrieve agent cards from Supabase
- **RLS Helpers** - Generate basic Row Level Security policies
- **Event Logging** - Track authentication events
- **Multi-Framework** - Works with FastAPI, Flask, and Django

## Development

```bash
# Clone the repository
git clone https://github.com/prassanna-ravishankar/phlow.git
cd phlow/packages/phlow-auth-python

# Install development dependencies
uv sync --extra dev

# Run tests
uv run pytest

# Format code
uv run black src tests
uv run isort src tests

# Type checking
uv run mypy src
```

## Documentation

- 📖 Documentation: https://prassanna.io/phlow/
- 🐛 Issues: https://github.com/prassanna-ravishankar/phlow/issues
- 💬 Discussions: https://github.com/prassanna-ravishankar/phlow/discussions

## License

MIT License - see LICENSE file for details.