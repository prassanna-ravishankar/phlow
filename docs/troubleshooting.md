# Troubleshooting

Common issues and solutions when working with Phlow.

## Authentication Issues

### "Invalid JWT token" Error

**Symptoms:**
```
AuthenticationError: Invalid JWT token
```

**Common Causes:**

1. **Clock Skew**: JWT tokens have timestamps that must be within acceptable time windows
   ```bash
   # Check system time is correct
   date
   # Sync system clock if needed
   sudo ntpdate -s time.nist.gov
   ```

2. **Wrong Private/Public Key Pair**: Ensure keys match
   ```python
   # Verify key pair matches
   from phlow.utils import verify_keypair
   is_valid = verify_keypair(private_key, public_key)
   ```

3. **Malformed Agent ID**: Agent ID in header doesn't match token claims
   ```python
   # Ensure agent_id matches between token and request header
   headers = {"X-Agent-ID": "same-agent-id-as-in-token"}
   ```

### "Agent not found in registry" Error

**Symptoms:**
```
AgentNotFoundError: Agent my-agent-id not found
```

**Solutions:**

1. **Check Supabase Registration**: Verify agent is in database
   ```sql
   SELECT * FROM agents WHERE agent_id = 'your-agent-id';
   ```

2. **Register Agent**: If not found, register first
   ```python
   await middleware.register_agent(agent_card)
   ```

3. **Check Agent ID Format**: Ensure consistent naming
   ```python
   # Agent ID should be URL-safe and consistent
   agent_id = "my-agent-2024"  # Good
   agent_id = "my agent!"      # Bad - spaces and special chars
   ```

## Supabase Connection Issues

### "Could not connect to Supabase" Error

**Symptoms:**
```
ConnectionError: Could not connect to Supabase
```

**Debugging Steps:**

1. **Verify Environment Variables**:
   ```bash
   echo $SUPABASE_URL
   echo $SUPABASE_ANON_KEY
   ```

2. **Test Connection**:
   ```python
   from supabase import create_client
   supabase = create_client(url, key)
   response = supabase.table('agents').select('*').limit(1).execute()
   print(response)
   ```

3. **Check Network Access**:
   ```bash
   curl -H "apikey: YOUR_ANON_KEY" "YOUR_SUPABASE_URL/rest/v1/"
   ```

### "RLS Policy Violation" Error

**Symptoms:**
```
PostgrestAPIError: new row violates row-level security policy
```

**Solutions:**

1. **Apply Database Schema**: Ensure RLS policies are set up
   ```bash
   psql -h db.xxx.supabase.co -U postgres -d postgres -f docs/database-schema.sql
   ```

2. **Check Service Role**: For admin operations, use service role key
   ```python
   # Use service role for admin operations
   supabase_admin = create_client(url, service_role_key)
   ```

## Performance Issues

### Slow Authentication

**Symptoms:**
- Authentication takes >2 seconds
- High CPU usage during JWT verification

**Solutions:**

1. **Enable Key Caching**: Use encrypted key store
   ```python
   from phlow.security import EncryptedFileKeyStore
   key_store = EncryptedFileKeyStore("/secure/path")
   ```

2. **Add Redis for Rate Limiting**: Reduce database load
   ```python
   rate_config = RateLimitConfig(
       redis_url="redis://localhost:6379"
   )
   ```

3. **Monitor Circuit Breakers**: Check if external calls are timing out
   ```python
   # Check circuit breaker status
   from phlow.monitoring import get_circuit_breaker_status
   status = get_circuit_breaker_status()
   ```

### Memory Leaks

**Symptoms:**
- Memory usage grows over time
- Application becomes slow after extended use

**Solutions:**

1. **Check HTTP Client Cleanup**: Ensure proper resource cleanup
   ```python
   # Always close HTTP clients
   async with httpx.AsyncClient() as client:
       # Use client here
       pass
   ```

2. **Monitor Cache Size**: DID document cache may grow large
   ```python
   # Configure cache size limits
   from phlow.rbac import configure_did_cache
   configure_did_cache(max_size=1000, ttl=3600)
   ```

## Development Issues

### Import Errors

**Symptoms:**
```
ImportError: cannot import name 'PhlowMiddleware'
```

**Solutions:**

1. **Check Installation**: Ensure Phlow is properly installed
   ```bash
   pip list | grep phlow
   uv pip install phlow[fastapi]  # With FastAPI support
   ```

2. **Virtual Environment**: Ensure you're in the correct environment
   ```bash
   which python
   pip show phlow
   ```

### Testing Issues

**Symptoms:**
- Tests fail with authentication errors
- Supabase connections in tests

**Solutions:**

1. **Use Test Configuration**: Mock Supabase for unit tests
   ```python
   from unittest.mock import Mock

   # Mock Supabase client
   mock_supabase = Mock()
   config.supabase_client = mock_supabase
   ```

2. **Environment Variables**: Set test environment
   ```bash
   export SUPABASE_URL="http://localhost:54321"
   export SUPABASE_ANON_KEY="test-key"
   ```

## Production Issues

### Rate Limiting Errors

**Symptoms:**
```
RateLimitExceededError: Rate limit exceeded for agent
```

**Solutions:**

1. **Increase Rate Limits**: Adjust configuration
   ```python
   rate_config = RateLimitConfig(
       requests_per_minute=120,  # Increase limit
       burst_size=30
   )
   ```

2. **Implement Backoff**: Add retry logic with exponential backoff
   ```python
   import asyncio

   async def retry_with_backoff(func, max_retries=3):
       for attempt in range(max_retries):
           try:
               return await func()
           except RateLimitExceededError:
               if attempt < max_retries - 1:
                   await asyncio.sleep(2 ** attempt)
               else:
                   raise
   ```

### Circuit Breaker Trips

**Symptoms:**
```
CircuitBreakerOpenError: Circuit breaker is open
```

**Solutions:**

1. **Check External Dependencies**: Verify Supabase/Redis health
   ```bash
   curl -f $SUPABASE_URL/health
   redis-cli ping
   ```

2. **Adjust Circuit Breaker Settings**: Tune thresholds
   ```python
   from phlow.monitoring import configure_circuit_breaker
   configure_circuit_breaker(
       failure_threshold=10,
       timeout_seconds=60
   )
   ```

## Monitoring and Debugging

### Enable Debug Logging

```python
import logging
logging.basicConfig(level=logging.DEBUG)

# Or use structured logging
from phlow.monitoring import configure_logging
configure_logging(level="DEBUG", format="json")
```

### Health Check Endpoints

```python
@app.get("/health")
async def health_check():
    try:
        # Test Supabase connection
        supabase.table('agents').select('agent_id').limit(1).execute()
        return {"status": "healthy", "timestamp": datetime.utcnow()}
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}
```

### Prometheus Metrics

```python
from phlow.monitoring import enable_prometheus_metrics
enable_prometheus_metrics(port=9090)

# Monitor these metrics:
# - phlow_auth_requests_total
# - phlow_auth_duration_seconds
# - phlow_rate_limit_hits_total
# - phlow_circuit_breaker_state
```

## Getting Help

### Enable Verbose Logging

```python
import os
os.environ["PHLOW_LOG_LEVEL"] = "DEBUG"
os.environ["PHLOW_ENABLE_AUDIT_LOGGING"] = "true"
```

### Collect Diagnostic Information

```python
from phlow.diagnostics import collect_diagnostics

# Generates diagnostic report
diagnostics = collect_diagnostics()
print(diagnostics)
```

### Common Log Patterns

**Successful Authentication:**
```json
{
  "level": "info",
  "message": "Agent authenticated successfully",
  "agent_id": "my-agent",
  "request_id": "req-123"
}
```

**Failed Authentication:**
```json
{
  "level": "warning",
  "message": "JWT verification failed",
  "agent_id": "my-agent",
  "error": "Token expired",
  "request_id": "req-124"
}
```

**Rate Limit Hit:**
```json
{
  "level": "warning",
  "message": "Rate limit exceeded",
  "agent_id": "my-agent",
  "current_rate": "65/min",
  "limit": "60/min"
}
```

Still having issues? Check the [GitHub Issues](https://github.com/prassanna-ravishankar/phlow/issues) or create a new issue with:

1. Phlow version (`pip show phlow`)
2. Python version (`python --version`)
3. Environment (development/production)
4. Complete error traceback
5. Minimal reproduction code
