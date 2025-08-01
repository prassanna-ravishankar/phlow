# Simple Phlow Agent Example

A minimal FastAPI application demonstrating Phlow authentication middleware.

## Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Environment Setup

Create a `.env` file:

```bash
# Supabase Configuration
SUPABASE_URL=your_supabase_project_url
SUPABASE_ANON_KEY=your_supabase_anon_key

# Agent Configuration
AGENT_ID=my-agent-001
AGENT_NAME=My Agent
AGENT_DESCRIPTION=A simple Phlow agent
AGENT_PERMISSIONS=read:data,write:data

# RSA Key Pair (generate with: openssl genrsa -out private.pem 2048)
AGENT_PUBLIC_KEY=-----BEGIN PUBLIC KEY-----...-----END PUBLIC KEY-----
AGENT_PRIVATE_KEY=-----BEGIN RSA PRIVATE KEY-----...-----END RSA PRIVATE KEY-----
```

### 3. Run the Agent

```bash
python main.py
```

The agent will start on `http://localhost:8000`

## API Endpoints

- `GET /health` - Health check
- `GET /info` - Agent information
- `GET /protected` - Protected endpoint (requires authentication)
- `GET /docs` - Interactive API documentation

## Testing

```bash
# Health check
curl http://localhost:8000/health

# Agent info
curl http://localhost:8000/info

# Protected endpoint (should return 401)
curl http://localhost:8000/protected
```

## Client Helper

The `client_helper.py` provides utilities for:
- Environment-based configuration
- Agent health monitoring
- Token generation for inter-agent communication

```python
from client_helper import create_client_from_env, check_agent_health

# Create client from environment variables
config = create_client_from_env()

# Check another agent's health
health = check_agent_health("http://other-agent:8000", "other-agent-id")
print(f"Agent status: {health['status']}")
```

## Learn More

- [Phlow Documentation](../../)
- [A2A Protocol](https://github.com/a2aproject)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)