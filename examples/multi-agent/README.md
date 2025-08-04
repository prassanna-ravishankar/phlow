# Multi-Agent A2A Communication Examples

This repository demonstrates two approaches to agent-to-agent communication using the A2A Protocol:

1. **Orchestrated Multi-Agent** (`main.py`) - External script controls the flow
2. **True A2A Multi-Agent** (`main_true_a2a.py`) - Agents discover and communicate autonomously

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Set environment variable (optional for AI responses)
export GEMINI_API_KEY="your-gemini-api-key"

# Run the orchestrated multi-agent demo
python main.py

# OR run the true A2A demo
python main_true_a2a.py
```

## Example 1: Orchestrated Multi-Agent (`main.py`)

### What This Demo Shows

1. **3 Specialized Agents** start on different ports:
   - **DataAnalyst** (port 8001): Data analysis and insights
   - **ContentWriter** (port 8002): Content creation and marketing
   - **CodeReviewer** (port 8003): Code review and engineering

2. **A2A Discovery**: Each agent discovers others via `/.well-known/agent.json`

3. **Agent-to-Agent Communication**:
   - DataAnalyst analyzes sales data
   - ContentWriter creates marketing content based on the analysis

### A2A Protocol Compliance

Each agent implements:

- ✅ **Agent Discovery**: `/.well-known/agent.json` endpoint
- ✅ **Task Processing**: `/tasks/send` endpoint
- ✅ **Specialized Capabilities**: Unique skills and descriptions
- ✅ **A2A Message Format**: Proper request/response structure

### Example Workflow

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

## Example 2: True A2A Multi-Agent (`main_true_a2a.py`)

This example demonstrates **true autonomous agent-to-agent communication** where agents:
- 🔍 Discover other agents based on capabilities
- 🤖 Make autonomous decisions about when to delegate
- 🔐 Authenticate with each other using Phlow's JWT tokens
- 🔄 Create complex workflows without external orchestration

### Key Differences from Orchestrated Example

| Aspect | Orchestrated (main.py) | True A2A (main_true_a2a.py) |
|--------|------------------------|------------------------------|
| **Control** | External script controls the flow | Agents make autonomous decisions |
| **Discovery** | Agents don't know about each other | Agents discover each other autonomously |
| **Communication** | Manual chaining of responses | Direct agent-to-agent HTTP calls with authentication |
| **Orchestration** | External orchestrator needed | No external orchestrator needed |

### How It Works

#### 1. Agent Registration
Each agent registers itself in a shared registry (in production, this would be Supabase):
```python
AGENT_REGISTRY[agent_id] = {
    "id": agent_id,
    "capabilities": ["data_analysis", "statistics"],
    "url": "http://127.0.0.1:8001"
}
```

#### 2. Capability Discovery
Agents can discover other agents by capability:
```python
def discover_agents_with_capability(capability: str) -> List[Dict]:
    matching_agents = []
    for agent_id, agent_data in AGENT_REGISTRY.items():
        if capability in agent_data.get("capabilities", []):
            matching_agents.append(agent_data)
    return matching_agents
```

#### 3. Authenticated Agent Calls
Agents authenticate when calling each other:
```python
# Generate JWT token
token = generate_token(my_agent_card, AGENT_PRIVATE_KEY)

# Make authenticated request
headers = {
    "Authorization": f"Bearer {token}",
    "Content-Type": "application/json"
}
```

#### 4. Intelligent Routing Logic

**DataAnalyst Agent**
- Analyzes data when requested
- If "marketing" or "content" mentioned → delegates to ContentWriter
- Combines its analysis with ContentWriter's marketing plan

**ContentWriter Agent**
- Creates content when requested
- If needs data analysis first → delegates to DataAnalyst
- Uses analyst's insights to create data-driven content

**CodeReviewer Agent**
- Reviews code when requested
- If task involves data/statistics → delegates to DataAnalyst

### Example Interactions

#### Example 1: ContentWriter needs data
```
User → ContentWriter: "Create marketing content for Q4 results with 25% growth"
ContentWriter → DataAnalyst: "Please analyze this for content creation"
DataAnalyst → ContentWriter: Returns analysis
ContentWriter → User: Data-driven marketing content
```

#### Example 2: DataAnalyst suggests marketing
```
User → DataAnalyst: "Analyze growth and suggest marketing strategies"
DataAnalyst: Performs analysis
DataAnalyst → ContentWriter: "Create marketing content based on this analysis"
ContentWriter → DataAnalyst: Returns marketing plan
DataAnalyst → User: Analysis + Marketing recommendations
```

### Try It Yourself

Once running, send requests to any agent:

```bash
# Ask ContentWriter (it will consult DataAnalyst)
curl -X POST http://localhost:8002/tasks/send \
  -H "Content-Type: application/json" \
  -d '{
    "id": "task-123",
    "message": {
      "role": "user",
      "parts": [{"type": "text", "text": "Create a blog post about our record-breaking sales data"}]
    }
  }'

# Ask DataAnalyst (it might engage ContentWriter)
curl -X POST http://localhost:8001/tasks/send \
  -H "Content-Type: application/json" \
  -d '{
    "id": "task-456",
    "message": {
      "role": "user",
      "parts": [{"type": "text", "text": "Analyze customer growth trends and recommend marketing actions"}]
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

## Production Considerations

1. **Use Supabase Registry**: Replace `AGENT_REGISTRY` with Supabase queries
2. **Real Authentication**: Use proper private/public key pairs
3. **Error Handling**: Add retries and circuit breakers
4. **Service Discovery**: Implement health checks and failover
5. **Rate Limiting**: Add Phlow's rate limiting for agent calls

## Architecture Benefits

- **Decentralized**: No single point of failure
- **Scalable**: Agents can be deployed independently
- **Flexible**: Easy to add new agents with new capabilities
- **Autonomous**: Agents make their own routing decisions
- **Secure**: All inter-agent communication is authenticated

## Features

- 🤖 **Specialized Agents** with unique capabilities
- 🔍 **Automatic Discovery** via A2A protocol
- 💬 **Inter-Agent Communication** with task delegation
- 🧠 **AI Integration Example** via Gemini (optional)
- 📊 **Real Workflow** demonstration (Data Analysis → Content Creation)
- 🔐 **Authenticated Communication** between agents
- 🚀 **Autonomous Decision Making** for task routing

This demonstrates the true power of the A2A Protocol with Phlow!
