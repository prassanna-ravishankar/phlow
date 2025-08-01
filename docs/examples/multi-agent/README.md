# Multi-Agent A2A Communication Example

Demonstrates specialized A2A agents discovering and communicating with each other.

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Set environment variable (optional for AI responses)
export GEMINI_API_KEY="your-gemini-api-key"

# Run the multi-agent demo
python main.py
```

## What This Demo Shows

1. **3 Specialized Agents** start on different ports:
   - **DataAnalyst** (port 8001): Data analysis and insights
   - **ContentWriter** (port 8002): Content creation and marketing
   - **CodeReviewer** (port 8003): Code review and engineering

2. **A2A Discovery**: Each agent discovers others via `/.well-known/agent.json`

3. **Agent-to-Agent Communication**: 
   - DataAnalyst analyzes sales data
   - ContentWriter creates marketing content based on the analysis

## A2A Protocol Compliance

Each agent implements:

- ✅ **Agent Discovery**: `/.well-known/agent.json` endpoint
- ✅ **Task Processing**: `/tasks/send` endpoint  
- ✅ **Specialized Capabilities**: Unique skills and descriptions
- ✅ **A2A Message Format**: Proper request/response structure

## Example Workflow

```bash
# 1. DataAnalyst analyzes data
curl -X POST http://localhost:8001/tasks/send \
  -H "Content-Type: application/json" \
  -d '{
    "id": "task-123",
    "message": {
      "role": "user",
      "parts": [{"type": "text", "text": "Sales increased 25% last quarter"}]
    }
  }'

# 2. ContentWriter creates content based on analysis
curl -X POST http://localhost:8002/tasks/send \
  -H "Content-Type: application/json" \
  -d '{
    "id": "task-456", 
    "message": {
      "role": "user",
      "parts": [{"type": "text", "text": "Create marketing content for 25% sales growth"}]
    }
  }'
```

## Agent Endpoints

While running, each agent exposes:

- **DataAnalyst**: http://localhost:8001
- **ContentWriter**: http://localhost:8002  
- **CodeReviewer**: http://localhost:8003

Each with:
- `/.well-known/agent.json` (A2A discovery)
- `/tasks/send` (A2A task processing)
- `/health` (health check)

## Features

- 🤖 **Specialized Agents** with unique capabilities
- 🔍 **Automatic Discovery** via A2A protocol
- 💬 **Inter-Agent Communication** with task delegation
- 🧠 **AI Integration Example** via Gemini (optional)
- 📊 **Real Workflow** demonstration (Data Analysis → Content Creation)

This example is based on the working `tests/test_e2e_multi_agent.py` and demonstrates real A2A Protocol multi-agent collaboration!