# Circuit Breakers Guide

Phlow includes circuit breakers to protect your agents from cascading failures when external dependencies become unavailable or degraded. Circuit breakers implement the "fail fast" pattern to improve system resilience.

## Overview

Circuit breakers prevent cascading failures by:
- **Monitoring** external dependency health
- **Opening** when failure thresholds are exceeded (fail fast)
- **Testing recovery** periodically (half-open state)
- **Closing** when dependencies recover (normal operation)

## How Circuit Breakers Work

### States

1. **CLOSED** (Normal): All requests pass through normally
2. **OPEN** (Failing Fast): Requests fail immediately without calling dependency
3. **HALF_OPEN** (Testing): Limited requests test if dependency has recovered

### State Transitions

```
CLOSED --[failures exceed threshold]--> OPEN
OPEN --[timeout expires]--> HALF_OPEN
HALF_OPEN --[successes]--> CLOSED
HALF_OPEN --[failure]--> OPEN
```

## Built-in Circuit Breakers

Phlow automatically uses circuit breakers for:

### 1. DID Resolution

Protects against external DID resolution failures:

```python
# Automatic circuit breaker for DID resolution
did_doc = await middleware._resolve_did_service_endpoint("did:web:example.com")
```

**Configuration:**
- Failure threshold: 5 failures
- Recovery timeout: 60 seconds
- Operation timeout: 15 seconds

### 2. Supabase Operations

Protects against database connection issues:

```python
# Circuit breaker automatically applied to Supabase operations
result = await supabase.table("agents").select("*").execute()
```

**Configuration:**
- Failure threshold: 3 failures
- Recovery timeout: 30 seconds
- Operation timeout: 10 seconds

### 3. A2A Messaging

Protects against agent communication failures:

```python
# Circuit breaker for A2A message sending
response = await middleware._send_role_credential_request(agent_id, request)
```

**Configuration:**
- Failure threshold: 3 failures
- Recovery timeout: 45 seconds
- Operation timeout: 20 seconds

## Manual Circuit Breaker Usage

### Basic Usage

```python
from phlow.circuit_breaker import circuit_breaker

@circuit_breaker("external_api")
async def call_external_api():
    async with httpx.AsyncClient() as client:
        response = await client.get("https://api.example.com/data")
        return response.json()

# Call protected function
try:
    data = await call_external_api()
except CircuitBreakerError:
    # Circuit is open, use fallback
    data = get_cached_data()
```

### Custom Configuration

```python
from phlow.circuit_breaker import CircuitBreaker, CircuitBreakerConfig

# Create custom circuit breaker
config = CircuitBreakerConfig(
    failure_threshold=10,      # 10 failures before opening
    recovery_timeout=120.0,    # 2 minutes before testing recovery
    timeout=30.0,              # 30 second operation timeout
    expected_exception=httpx.HTTPError  # Only count HTTP errors
)

breaker = CircuitBreaker("my_service", config)

# Use with any function
async def risky_operation():
    # Your code here
    pass

try:
    result = await breaker.acall(risky_operation)
except CircuitBreakerError:
    # Handle circuit open
    pass
```

### Registry Usage

```python
from phlow.circuit_breaker import get_circuit_breaker_registry

registry = get_circuit_breaker_registry()

# Get existing breaker or create new one
breaker = registry.get_breaker("payment_service", config)

# Get statistics for all breakers
stats = registry.get_stats()
print(stats)
# {
#   "payment_service": {
#     "state": "closed",
#     "failure_count": 2,
#     "success_count": 0,
#     "failure_threshold": 5
#   }
# }
```

## FastAPI Integration

### Health Check Endpoint

```python
from fastapi import FastAPI
from phlow.circuit_breaker import get_circuit_breaker_registry

app = FastAPI()

@app.get("/health/circuit-breakers")
async def circuit_breaker_health():
    """Get circuit breaker status for monitoring."""
    registry = get_circuit_breaker_registry()
    stats = registry.get_stats()

    # Check if any breakers are open
    open_breakers = [
        name for name, stat in stats.items()
        if stat["state"] == "open"
    ]

    return {
        "status": "healthy" if not open_breakers else "degraded",
        "open_breakers": open_breakers,
        "breaker_stats": stats
    }
```

### Graceful Degradation

```python
from phlow.circuit_breaker import CircuitBreakerError

@app.post("/api/user-info")
async def get_user_info(user_id: str):
    try:
        # Try to get fresh data
        user_data = await fetch_user_from_external_api(user_id)
    except CircuitBreakerError:
        # Circuit is open, use cached data
        user_data = await get_cached_user_data(user_id)
        if not user_data:
            raise HTTPException(
                status_code=503,
                detail="Service temporarily unavailable"
            )

    return user_data
```

## Configuration Examples

### High-Traffic Service

```python
# For high-traffic, low-latency services
config = CircuitBreakerConfig(
    failure_threshold=20,      # Higher threshold
    recovery_timeout=30.0,     # Quick recovery attempts
    timeout=5.0,               # Fast timeout
    expected_exception=httpx.HTTPError
)
```

### Critical External Service

```python
# For critical services that should fail fast
config = CircuitBreakerConfig(
    failure_threshold=2,       # Very low threshold
    recovery_timeout=300.0,    # Long recovery time
    timeout=10.0,              # Reasonable timeout
    expected_exception=Exception  # Catch all errors
)
```

### Unreliable Third-Party API

```python
# For unreliable third-party services
config = CircuitBreakerConfig(
    failure_threshold=10,      # Tolerate some failures
    recovery_timeout=60.0,     # Regular recovery checks
    timeout=30.0,              # Generous timeout
    expected_exception=(httpx.HTTPError, asyncio.TimeoutError)
)
```

## Monitoring and Alerting

### Logging

Circuit breakers automatically log state changes:

```json
{
  "timestamp": 1705320645.123,
  "level": "warning",
  "message": "Circuit breaker external_api opened",
  "failure_count": 5,
  "threshold": 5
}
```

### Metrics Integration

```python
# Circuit breaker metrics are automatically collected
from phlow.monitoring import get_metrics_collector

collector = get_metrics_collector()
metrics = collector.get_metrics_dict()

# Check circuit breaker states in your monitoring
```

### Prometheus Alerts

```yaml
# Example Prometheus alerting rules
groups:
  - name: circuit_breakers
    rules:
      - alert: CircuitBreakerOpen
        expr: phlow_circuit_breaker_state{state="open"} == 1
        for: 1m
        labels:
          severity: warning
        annotations:
          summary: "Circuit breaker {{ $labels.name }} is open"
          description: "Circuit breaker for {{ $labels.name }} has been open for over 1 minute"

      - alert: HighCircuitBreakerFailures
        expr: rate(phlow_circuit_breaker_failures_total[5m]) > 0.1
        for: 2m
        labels:
          severity: warning
        annotations:
          summary: "High circuit breaker failure rate"
          description: "Circuit breaker {{ $labels.name }} is experiencing {{ $value }} failures per second"
```

## Best Practices

### 1. Choose Appropriate Thresholds

- **Low thresholds** (2-3): Critical services that must fail fast
- **Medium thresholds** (5-10): Regular external services
- **High thresholds** (10+): High-traffic, occasionally unreliable services

### 2. Set Reasonable Timeouts

- **Short timeouts** (1-5s): User-facing operations
- **Medium timeouts** (10-30s): Background processing
- **Long timeouts** (60s+): Batch operations

### 3. Implement Fallbacks

Always have a fallback strategy when circuit breakers open:

```python
async def get_user_data(user_id: str):
    try:
        return await fetch_from_primary_service(user_id)
    except CircuitBreakerError:
        # Try secondary service
        try:
            return await fetch_from_backup_service(user_id)
        except CircuitBreakerError:
            # Use cached data
            return await get_cached_data(user_id)
```

### 4. Monitor Circuit Breaker Health

- Set up alerts for when breakers open
- Monitor failure rates and recovery times
- Review and adjust thresholds based on real usage

### 5. Test Circuit Breaker Behavior

```python
# Test circuit breaker opens correctly
async def test_circuit_breaker_opens():
    breaker = CircuitBreaker("test", CircuitBreakerConfig(failure_threshold=2))

    # Cause failures
    for _ in range(3):
        try:
            await breaker.acall(lambda: exec('raise Exception("test")'))
        except:
            pass

    # Should be open now
    assert breaker.state == CircuitBreakerState.OPEN

    # Next call should fail fast
    with pytest.raises(CircuitBreakerError):
        await breaker.acall(lambda: "success")
```

## Troubleshooting

### Circuit Breaker Stuck Open

**Symptoms**: Breaker never recovers even when service is healthy

**Solutions**:
- Check if recovery timeout is too long
- Verify the service is actually healthy
- Manually reset: `registry.reset_breaker("service_name")`

### Too Many False Positives

**Symptoms**: Breaker opens frequently for temporary issues

**Solutions**:
- Increase failure threshold
- Adjust timeout values
- Use more specific exception types

### Performance Impact

**Symptoms**: Circuit breaker adds too much latency

**Solutions**:
- Circuit breakers have minimal overhead (~1ms)
- Check if timeouts are too aggressive
- Ensure proper async/await usage

### Configuration Not Applied

**Symptoms**: Breaker uses default configuration

**Solutions**:
- Verify configuration is passed to constructor
- Check if breaker already exists with different config
- Use registry to manage breaker lifecycle

## Examples

### Database Circuit Breaker

```python
@circuit_breaker(
    "database",
    failure_threshold=3,
    recovery_timeout=60.0,
    timeout=10.0
)
async def query_database(query: str):
    async with database_pool.acquire() as conn:
        return await conn.fetch(query)
```

### External API with Retry

```python
async def call_with_retry_and_circuit_breaker(url: str, max_retries: int = 3):
    breaker = get_circuit_breaker_registry().get_breaker("external_api")

    for attempt in range(max_retries):
        try:
            return await breaker.acall(lambda: httpx.get(url))
        except CircuitBreakerError:
            # Circuit is open, don't retry
            raise
        except httpx.HTTPError:
            if attempt == max_retries - 1:
                raise
            await asyncio.sleep(2 ** attempt)  # Exponential backoff
```

Circuit breakers are a powerful tool for building resilient systems. Use them to protect against cascading failures and improve your agent's reliability in distributed environments.
