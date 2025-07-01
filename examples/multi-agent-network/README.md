# Multi-Agent Network Example

This example demonstrates a complex multi-agent system using Phlow for authentication, showcasing how multiple specialized agents can work together in coordinated workflows.

## Architecture

The network consists of 4 agents:

```
┌─────────────────┐    ┌──────────────────┐
│   Coordinator   │◄──►│   Data Agent     │
│   Agent         │    │   (Storage)      │
│   (Orchestrator)│    └──────────────────┘
│                 │
│                 │    ┌──────────────────┐
│                 │◄──►│   Auth Agent     │
│                 │    │   (Security)     │
│                 │    └──────────────────┘
│                 │
│                 │    ┌──────────────────┐
│                 │◄──►│  Compute Agent   │
│                 │    │  (Processing)    │
└─────────────────┘    └──────────────────┘
```

### Agent Responsibilities

- **Coordinator Agent** (Port 4000): Orchestrates workflows, manages inter-agent communication
- **Data Agent** (Port 4001): Handles data storage, retrieval, and dataset management  
- **Auth Agent** (Port 4002): Manages user authentication, validation, and audit logging
- **Compute Agent** (Port 4003): Performs computational tasks, data analysis, and processing

## Features

- ✅ Inter-agent authentication using JWT tokens
- ✅ Complex multi-step workflows
- ✅ Permission-based access control between agents
- ✅ Audit logging across all agents
- ✅ Error handling and fault tolerance
- ✅ Real-time network status monitoring

## Setup

1. **Install dependencies**:
   ```bash
   npm install
   ```

2. **Set up Supabase**:
   - Create a new Supabase project
   - Run the SQL schema from the main phlow CLI package
   - Update environment variables with your credentials

3. **Generate agent keys**:
   ```bash
   # Generate keys for each agent using the phlow CLI
   phlow init  # For each agent configuration
   ```

4. **Configure environment**:
   ```bash
   cp .env.example .env
   # Edit .env with your Supabase credentials and agent keys
   ```

## Running the Network

### Option 1: Run all agents simultaneously
```bash
npm run dev
```

### Option 2: Run agents individually
```bash
# Terminal 1 - Data Agent
npm run start:data

# Terminal 2 - Auth Agent  
npm run start:auth

# Terminal 3 - Compute Agent
npm run start:compute

# Terminal 4 - Coordinator
npm start
```

## Available Workflows

### 1. User Analysis Workflow
Demonstrates cross-agent collaboration for user behavior analysis.

```bash
curl "http://localhost:4000/workflow/user-analysis?userId=user-123" \
  -H "Authorization: Bearer <token>" \
  -H "X-Phlow-Agent-Id: <your-agent-id>"
```

**Flow**:
1. Coordinator receives request
2. Auth Agent validates user
3. Data Agent fetches user profile
4. Compute Agent analyzes behavior
5. Data Agent stores results

### 2. Data Processing Workflow
Shows how agents collaborate to process datasets.

```bash
curl -X POST "http://localhost:4000/workflow/data-processing" \
  -H "Authorization: Bearer <token>" \
  -H "X-Phlow-Agent-Id: <your-agent-id>" \
  -H "Content-Type: application/json" \
  -d '{
    "dataset": "sales-data",
    "operation": "sum"
  }'
```

**Flow**:
1. Coordinator receives processing request
2. Data Agent validates dataset access
3. Data Agent retrieves dataset
4. Compute Agent processes data
5. Data Agent stores results

### 3. System Status Workflow
Aggregates status from all agents in the network.

```bash
curl "http://localhost:4000/workflow/system-status" \
  -H "Authorization: Bearer <token>" \
  -H "X-Phlow-Agent-Id: <your-agent-id>"
```

## Network Monitoring

### Check overall network status:
```bash
curl http://localhost:4000/network/status
```

### Check individual agent health:
```bash
curl http://localhost:4001/health  # Data Agent
curl http://localhost:4002/health  # Auth Agent
curl http://localhost:4003/health  # Compute Agent
curl http://localhost:4000/health  # Coordinator
```

## Testing

Run the comprehensive network test suite:

```bash
npm test
```

This tests:
- Individual agent health
- Inter-agent authentication
- Complete workflow execution
- Error handling and recovery

## Agent APIs

### Coordinator Agent (Port 4000)
- `GET /` - Network overview
- `GET /network/status` - Network health status
- `GET /workflow/user-analysis` - User analysis workflow
- `POST /workflow/data-processing` - Data processing workflow
- `GET /workflow/system-status` - System status workflow

### Data Agent (Port 4001)
- `GET /users/profile` - User profile retrieval
- `POST /datasets/validate` - Dataset access validation
- `GET /datasets/:id` - Dataset retrieval
- `POST /analytics/store` - Store analysis results

### Auth Agent (Port 4002)  
- `POST /validate-user` - User validation
- `POST /check-permissions` - Permission checking
- `POST /sessions/create` - Session management
- `GET /audit/logs` - Authentication audit logs

### Compute Agent (Port 4003)
- `POST /analyze` - Data analysis tasks
- `POST /process` - Dataset processing
- `GET /tasks/:id` - Task status checking

## Authentication Flow

1. **Coordinator** generates a JWT token for the target agent
2. **Token includes**:
   - Coordinator's agent ID (issuer)
   - Target agent ID (audience)  
   - Required permissions
   - Expiration time

3. **Target agent** verifies token using Coordinator's public key
4. **Access granted** based on token validity and permissions

## Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `SUPABASE_URL` | Your Supabase project URL | Yes |
| `SUPABASE_ANON_KEY` | Your Supabase anon key | Yes |
| `COORDINATOR_PORT` | Coordinator agent port | No (default: 4000) |
| `DATA_AGENT_PORT` | Data agent port | No (default: 4001) |
| `AUTH_AGENT_PORT` | Auth agent port | No (default: 4002) |
| `COMPUTE_AGENT_PORT` | Compute agent port | No (default: 4003) |
| `*_PUBLIC_KEY` | RSA public keys for each agent | Yes |
| `*_PRIVATE_KEY` | RSA private keys for each agent | Yes |

## Security Considerations

- 🔒 Each agent has its own RSA key pair
- 🔄 Tokens are short-lived (10 minutes) for inter-agent communication
- 🚫 All inter-agent requests are authenticated and audited
- ⚡ Rate limiting prevents abuse
- 📊 Comprehensive audit logging across all agents

## Troubleshooting

### Common Issues

1. **"Agent not found" errors**
   - Ensure all agent cards are registered in Supabase
   - Check that agent IDs match in configuration

2. **Connection refused errors**
   - Verify all agents are running on their configured ports
   - Check that ports are not blocked by firewall

3. **Authentication failures**
   - Verify RSA key pairs match between agents
   - Check that tokens haven't expired
   - Ensure agent has required permissions

4. **Workflow timeouts**
   - Check individual agent health
   - Verify network connectivity between agents
   - Review agent logs for specific errors

### Debug Mode

Enable debug logging for all agents:

```bash
DEBUG=phlow:* npm run dev
```

### Network Diagnostics

Use the built-in network status endpoint to diagnose issues:

```bash
curl http://localhost:4000/network/status | jq
```

This will show the status of all agents and help identify which ones are offline or experiencing issues.