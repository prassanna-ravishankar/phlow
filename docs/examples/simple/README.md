# Simple A2A Agent Example

A minimal A2A Protocol compliant agent using Phlow framework.

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Set environment variable (optional for AI responses)
export GEMINI_API_KEY="your-gemini-api-key"

# Run the agent
python main.py
```

## A2A Protocol Compliance

This agent implements the required A2A Protocol endpoints:

### 1. Agent Discovery
```bash
curl http://localhost:8000/.well-known/agent.json
```

### 2. Task Execution
```bash
curl -X POST http://localhost:8000/tasks/send \
  -H "Content-Type: application/json" \
  -d '{
    "id": "task-123",
    "message": {
      "role": "user", 
      "parts": [{"type": "text", "text": "Hello from another agent!"}]
    }
  }'
```

## Features

- ✅ **A2A Agent Card** at `/.well-known/agent.json`
- ✅ **A2A Task Endpoint** at `/tasks/send`
- ✅ **AI Integration Example** (Gemini, optional)
- ✅ **Error Handling** with A2A-compliant responses
- ✅ **Legacy Endpoints** for backward compatibility

## Response Format

All task responses follow the A2A Protocol format:

```json
{
  "id": "task-123",
  "status": {"state": "completed", "message": "Task completed successfully"},
  "messages": [{
    "role": "agent",
    "parts": [{"type": "text", "text": "Agent response"}]
  }],
  "metadata": {"agent_id": "phlow-simple-agent-001", "framework": "phlow"}
}
```

## Development

This example is based on the working E2E test structure in `tests/test_e2e.py` and demonstrates real A2A Protocol compliance.