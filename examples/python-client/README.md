# Python Phlow Agent Example

This example demonstrates how to create a Python-based agent using FastAPI and Phlow authentication middleware.

## Features

- ✅ FastAPI integration with automatic dependency injection
- ✅ JWT-based authentication with Phlow middleware
- ✅ Permission-based access control
- ✅ Rate limiting and audit logging
- ✅ Token generation for inter-agent communication
- ✅ Comprehensive error handling
- ✅ Interactive API documentation (Swagger/OpenAPI)
- ✅ Python client helper utilities

## Setup

### 1. Install Dependencies

```bash
# Install with uv (recommended)
uv pip install -e ".[examples]"

# Or with pip
pip install -e ".[examples]"
```

### 2. Environment Configuration

```bash
cp .env.example .env
# Edit .env with your configuration
```

Required environment variables:

| Variable | Description | Example |
|----------|-------------|---------|
| `SUPABASE_URL` | Your Supabase project URL | `https://xyz.supabase.co` |
| `SUPABASE_ANON_KEY` | Your Supabase anon key | `eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...` |
| `AGENT_ID` | Unique agent identifier | `python-agent-001` |
| `AGENT_NAME` | Human-readable agent name | `Python Agent Example` |
| `AGENT_PUBLIC_KEY` | RSA public key (PEM format) | `-----BEGIN PUBLIC KEY-----\n...` |
| `AGENT_PRIVATE_KEY` | RSA private key (PEM format) | `-----BEGIN RSA PRIVATE KEY-----\n...` |

Optional environment variables:

| Variable | Description | Default |
|----------|-------------|---------|
| `AGENT_DESCRIPTION` | Agent description | `A Python-based Phlow agent using FastAPI` |
| `AGENT_PERMISSIONS` | Comma-separated permissions | `read:data,write:data` |
| `PORT` | Server port | `8000` |
| `ENVIRONMENT` | Deployment environment | `development` |
| `RATE_LIMIT_REQUESTS` | Max requests per window | `100` |
| `RATE_LIMIT_WINDOW_MS` | Rate limit window in ms | `60000` |

### 3. Generate Agent Keys

If you don't have RSA keys yet, you can generate them using the Phlow CLI:

```bash
# Install Phlow CLI globally
pip install phlow

# Initialize and generate keys
phlow init
```

Or generate them manually with OpenSSL:

```bash
# Generate private key
openssl genpkey -algorithm RSA -out private_key.pem -pkcs8 -pass pass:your_password

# Generate public key
openssl rsa -pubout -in private_key.pem -out public_key.pem
```

## Running the Agent

### Development Mode

```bash
python main.py
```

The agent will start on `http://localhost:8000` with auto-reload enabled.

### Production Mode

```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4
```

### Using Docker

```bash
# Build image
docker build -t python-phlow-agent .

# Run container
docker run -p 8000:8000 --env-file .env python-phlow-agent
```

## API Endpoints

### Public Endpoints

- `GET /` - Agent information and available endpoints
- `GET /health` - Health check
- `GET /docs` - Interactive API documentation (Swagger UI)
- `GET /redoc` - Alternative API documentation

### Protected Endpoints (Require Authentication)

- `GET /protected` - Basic authentication test
- `GET /agent-info` - Detailed agent and token information
- `POST /generate-token` - Generate tokens for other agents

### Permission-Based Endpoints

- `GET /data` - Requires `read:data` permission
- `POST /data` - Requires `write:data` permission
- `GET /admin` - Requires `admin:users` permission

## Authentication

### Making Requests to This Agent

```python
import requests
from phlow import generate_token

# Generate token
token = generate_token(
    your_agent_card,
    your_private_key,
    "python-agent-001",  # Target agent ID
    "1h"
)

# Make authenticated request
response = requests.get(
    "http://localhost:8000/protected",
    headers={
        "Authorization": f"Bearer {token}",
        "X-Phlow-Agent-Id": "your-agent-id",
    }
)
```

### Using the Python Client Helper

```python
from client_helper import create_client_from_env

# Create client from environment variables
client = create_client_from_env()

# Make authenticated requests easily
response = client.get("http://localhost:8000/protected", "python-agent-001")
print(response.json())

# Test agent health
health = client.check_agent_health("http://localhost:8000", "python-agent-001")
print(f"Agent status: {health['status']}")
```

## Testing

### Run Integration Tests

```bash
python test_client.py
```

This will test:
- Public endpoints
- Authentication requirements
- Permission-based access control
- Token generation
- Error handling
- Async functionality

### Manual Testing with curl

```bash
# Test public endpoint
curl http://localhost:8000/

# Test health check
curl http://localhost:8000/health

# Test protected endpoint (should fail)
curl http://localhost:8000/protected

# Test with authentication (replace with actual token)
curl -H "Authorization: Bearer your-jwt-token" \
     -H "X-Phlow-Agent-Id: your-agent-id" \
     http://localhost:8000/protected
```

### Interactive Testing

Visit `http://localhost:8000/docs` for interactive API documentation where you can test endpoints directly from your browser.

## Client Helper Usage

The `client_helper.py` module provides utilities for Python clients:

### Basic Usage

```python
from client_helper import PhlowClient, PhlowClientConfig, AgentDiscovery
from phlow import AgentCard

# Create client configuration
config = PhlowClientConfig(
    agent_card=your_agent_card,
    private_key=your_private_key
)

client = PhlowClient(config)

# Make requests
response = client.get("http://target-agent:8000/data", "target-agent-id")
response = client.post("http://target-agent:8000/data", "target-agent-id", {
    "name": "New Data",
    "value": 42
})
```

### Agent Discovery

```python
# Discover agents in your network
discovery = AgentDiscovery(client)

# Discover a specific agent
result = discovery.discover_agent("http://agent:8000", "agent-id")
print(f"Agent health: {result['health']['status']}")

# Find agents with specific capabilities
data_agents = discovery.find_agents_with_capability("read:data")
admin_agents = discovery.find_agents_with_capability("admin:users")
```

### Batch Requests

```python
# Make multiple requests in batch
requests_data = [
    {"method": "GET", "url": "http://agent1:8000/health"},
    {"method": "GET", "url": "http://agent2:8000/data"},
    {"method": "POST", "url": "http://agent3:8000/process", "data": {"task": "analyze"}},
]

results = client.batch_request(requests_data, "target-agent-id")
for result in results:
    if result["success"]:
        print(f"✅ {result['request']['url']}: {result['status_code']}")
    else:
        print(f"❌ {result['request']['url']}: {result['error']}")
```

## FastAPI Integration Details

### Dependency Injection

The agent uses FastAPI's dependency injection system for authentication:

```python
from phlow.integrations.fastapi import create_phlow_dependency

# Create authentication dependencies
auth_required = create_phlow_dependency(phlow)
admin_required = create_phlow_dependency(phlow, required_permissions=["admin:users"])

@app.get("/protected")
async def protected_endpoint(context: PhlowContext = Depends(auth_required)):
    # context.agent contains the requesting agent's information
    # context.claims contains the JWT claims
    return {"message": f"Hello {context.agent.name}!"}
```

### Custom Middleware

You can also create custom middleware for more control:

```python
@app.middleware("http")
async def phlow_middleware(request: Request, call_next):
    # Custom authentication logic
    if request.url.path.startswith("/protected"):
        # Extract and verify token
        # Add context to request state
        pass
    
    response = await call_next(request)
    return response
```

### Error Handling

The agent includes comprehensive error handling:

```python
@app.exception_handler(AuthenticationError)
async def authentication_error_handler(request, exc):
    return HTTPException(
        status_code=401,
        detail={
            "error": "Authentication failed",
            "code": exc.code,
            "message": exc.message,
        }
    )
```

## Configuration Examples

### Production Configuration

```python
# main.py - Production settings
if os.getenv("ENVIRONMENT") == "production":
    # Disable debug mode
    app = FastAPI(debug=False)
    
    # Stricter rate limiting
    config.rate_limiting = {
        "max_requests": 50,
        "window_ms": 60000,
    }
    
    # Enable all security features
    config.enable_audit = True
```

### Development Configuration

```python
# main.py - Development settings
if os.getenv("ENVIRONMENT") == "development":
    # Enable debug mode
    app = FastAPI(debug=True)
    
    # Relaxed rate limiting
    config.rate_limiting = {
        "max_requests": 1000,
        "window_ms": 60000,
    }
```

## Deployment

### Docker Deployment

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY pyproject.toml .
RUN pip install --no-cache-dir -e ".[examples]"

COPY . .

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Environment-Specific Configs

```bash
# Development
export ENVIRONMENT=development
export PORT=8000
export RATE_LIMIT_REQUESTS=1000

# Production
export ENVIRONMENT=production
export PORT=80
export RATE_LIMIT_REQUESTS=100
```

## Monitoring and Observability

### Health Checks

The agent provides comprehensive health information:

```python
@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "agent_id": agent_card.agent_id,
        "timestamp": datetime.utcnow().isoformat(),
        "version": "1.0.0",
        # Add custom health metrics here
    }
```

### Metrics Collection

Add custom metrics to monitor your agent:

```python
# Track request counts, response times, etc.
@app.middleware("http")
async def metrics_middleware(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    
    # Log metrics
    logger.info(f"Request: {request.method} {request.url.path} - {response.status_code} - {process_time:.3f}s")
    
    return response
```

## Security Best Practices

1. **Environment Variables**: Never commit `.env` files to version control
2. **Key Management**: Store private keys securely, rotate regularly
3. **HTTPS**: Always use HTTPS in production
4. **Rate Limiting**: Configure appropriate rate limits for your use case
5. **Audit Logging**: Enable audit logging for security monitoring
6. **Input Validation**: Validate all input data using Pydantic models
7. **Error Handling**: Don't expose sensitive information in error messages

## Troubleshooting

### Common Issues

1. **"Missing required environment variable"**
   - Check that all required variables are set in your `.env` file

2. **"Authentication failed"**
   - Verify that your agent is registered in Supabase
   - Check that the public/private key pair matches
   - Ensure the token hasn't expired

3. **"Insufficient permissions"**
   - Check that your agent has the required permissions
   - Verify permissions are correctly set in the agent card

4. **"Rate limit exceeded"**
   - Implement backoff and retry logic in your client
   - Consider increasing rate limits if appropriate

### Debug Mode

Enable debug logging:

```python
import logging
logging.getLogger("phlow").setLevel(logging.DEBUG)
logging.getLogger("uvicorn").setLevel(logging.DEBUG)
```

### Testing Connectivity

```python
# Test if agent is reachable
import requests
try:
    response = requests.get("http://localhost:8000/health", timeout=5)
    print(f"Agent is reachable: {response.status_code}")
except requests.exceptions.RequestException as e:
    print(f"Agent is not reachable: {e}")
```

## Next Steps

- 📖 Read the [main documentation](../../docs/getting-started.md)
- 🔍 Explore other [examples](../)
- 🧪 Run [integration tests](../../tests/integration/)
- 📖 Read the [main documentation](../../docs/getting-started.md)