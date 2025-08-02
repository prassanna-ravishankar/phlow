# Quick Start

Get a Phlow A2A-compliant agent running in 5 minutes.

## Prerequisites

- Python 3.10+
- Docker (for E2E testing)
- UV package manager (recommended) or pip

## Install

```bash
# Using UV (recommended)
uv add phlow

# Or using pip
pip install phlow
```

## Create Your A2A Agent

```python
from fastapi import FastAPI, Request
from phlow import AgentCard, PhlowConfig
from phlow.integrations.fastapi import FastAPIPhlowAuth
import os

app = FastAPI(title="My A2A Agent")

# 1. Configure your agent
config = PhlowConfig(
    agent_card=AgentCard(
        name="My AI Agent",
        description="A2A Protocol compliant AI assistant",
        service_url="https://my-agent.com",
        skills=["chat", "analysis", "reasoning"],
        metadata={
            "agent_id": "my-agent-001",
            "public_key": os.getenv("PUBLIC_KEY"),
            "model": "gemini-2.5-flash-lite"
        }
    ),
    private_key=os.getenv("PRIVATE_KEY"),
    supabase_url=os.getenv("SUPABASE_URL"),
    supabase_anon_key=os.getenv("SUPABASE_ANON_KEY")
)

auth = FastAPIPhlowAuth(config)

# 2. A2A Agent Card Discovery (required by A2A protocol)
@app.get("/.well-known/agent.json")
def agent_card():
    """A2A Agent Card for discovery"""
    return {
        "id": config.agent_card.metadata.get("agent_id"),
        "name": config.agent_card.name,
        "description": config.agent_card.description,
        "capabilities": {skill: True for skill in config.agent_card.skills},
        "input_modes": ["text"],
        "output_modes": ["text"],
        "endpoints": {
            "task": "/tasks/send"
        },
        "metadata": config.agent_card.metadata
    }

# 3. A2A Task Endpoint (required by A2A protocol)
@app.post("/tasks/send")
@auth.require_agent_auth
async def send_task(request: Request, task: dict):
    """A2A Protocol task endpoint"""
    # Extract message from A2A format
    message_text = ""
    if "message" in task and "parts" in task["message"]:
        for part in task["message"]["parts"]:
            if part.get("type") == "text":
                message_text += part.get("text", "")

    # Process with your AI (integrate Gemini, OpenAI, etc.)
    response_text = f"Hello! I received: {message_text}"

    # Return A2A-compliant response
    return {
        "id": task.get("id"),
        "status": {"state": "completed", "message": "Task completed"},
        "messages": [{
            "role": "agent",
            "parts": [{"type": "text", "text": response_text}]
        }],
        "metadata": {"agent_id": config.agent_card.metadata.get("agent_id")}
    }

# 4. Protected endpoints
@app.post("/api/chat")
@auth.require_agent_auth
async def chat(request: Request):
    agent = request.state.agent
    return {"message": f"Hello from {agent.name}"}
```

## Setup Environment

### Step 1: Generate RSA Keys

```bash
# Generate RSA key pair
openssl genrsa -out private_key.pem 2048
openssl rsa -in private_key.pem -pubout -out public_key.pem

# Convert to single-line format for environment variables
PRIVATE_KEY=$(awk 'NF {sub(/\r/, ""); printf "%s\\n",$0;}' private_key.pem)
PUBLIC_KEY=$(awk 'NF {sub(/\r/, ""); printf "%s\\n",$0;}' public_key.pem)
```

### Step 2: Setup Supabase

1. **Create Supabase Project**: Go to [supabase.com](https://supabase.com) and create a new project

2. **Get API Keys**: From Settings > API, copy:
   - Project URL
   - `anon` key (public)
   - `service_role` key (secret, for admin operations)

3. **Setup Database Schema**:
   ```bash
   # Apply Phlow database schema
   curl -o schema.sql https://raw.githubusercontent.com/prassanna-ravishankar/phlow/main/docs/database-schema.sql

   # Apply to your Supabase database (replace with your project details)
   psql "postgresql://postgres:[PASSWORD]@db.[PROJECT-ID].supabase.co:5432/postgres" -f schema.sql
   ```

### Step 3: Set Environment Variables

```bash
# Create .env file with your actual values
cat > .env << EOF
# RSA Keys (generated above)
PRIVATE_KEY="$PRIVATE_KEY"
PUBLIC_KEY="$PUBLIC_KEY"

# Supabase Configuration
SUPABASE_URL="https://your-project-id.supabase.co"
SUPABASE_ANON_KEY="your-anon-key-from-supabase"
SUPABASE_SERVICE_ROLE_KEY="your-service-role-key-from-supabase"

# Agent Configuration
AGENT_ID="my-agent-$(date +%s)"
AGENT_NAME="My AI Agent"
AGENT_DESCRIPTION="A2A Protocol compliant AI assistant"
AGENT_PERMISSIONS="read:messages,write:responses"

# Optional: AI Provider Keys
GEMINI_API_KEY="your-gemini-api-key"
OPENAI_API_KEY="your-openai-api-key"
EOF

# Load environment variables
source .env
```

## Run Your Agent

```bash
# Using taskipy (if developing Phlow)
uv run task dev-example

# Or directly with uvicorn
uvicorn your_agent:app --host 0.0.0.0 --port 8000
```

## Test A2A Compliance

```bash
# 1. Test A2A Agent Card Discovery
curl http://localhost:8000/.well-known/agent.json

# 2. Test A2A Task Endpoint
curl -X POST http://localhost:8000/tasks/send \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -d '{
    "id": "task-123",
    "message": {
      "role": "user",
      "parts": [{"type": "text", "text": "Hello from another agent!"}]
    }
  }'
```

## Development Commands

Phlow uses [taskipy](https://github.com/taskipy/taskipy) for task management:

```bash
# See all available tasks
uv run task --list

# Run tests
uv run task test-unit          # Unit tests
uv run task test-e2e           # E2E tests (requires Docker)
uv run task test-e2e-multi     # Multi-agent communication tests

# Code quality
uv run task lint               # Lint code
uv run task format             # Format code
uv run task type-check         # Type checking

# Build and release
uv run task build              # Build package
uv run task clean              # Clean artifacts
```

---

**Next Steps:**
- [Installation Guide](installation.md) - Detailed setup
- [Configuration](configuration.md) - All options
- [A2A Compatibility](a2a-compatibility.md) - Protocol compliance
- [Multi-Agent Guide](examples/multi-agent.md) - Agent networks
