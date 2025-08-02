# Distributed Rate Limiting Guide

Phlow includes distributed rate limiting to protect your agents from abuse and ensure fair resource usage across multiple instances.

## Overview

The rate limiting system provides:
- **Distributed limiting** - Works across multiple instances using Redis
- **Automatic fallback** - Falls back to in-memory limiting if Redis is unavailable
- **Sliding window algorithm** - Accurate request counting over time
- **Multiple limit types** - Different limits for authentication and role requests

## Configuration

### Basic Setup (In-Memory)

By default, Phlow uses in-memory rate limiting which works for single instances:

```python
from phlow import PhlowMiddleware, PhlowConfig

# Rate limits are configured automatically:
# - Authentication: 60 requests per minute
# - Role requests: 10 requests per minute
middleware = PhlowMiddleware(config)
```

### Distributed Setup (Redis)

For production deployments with multiple instances, enable Redis:

```bash
# Set Redis URL in environment
export REDIS_URL="redis://localhost:6379/0"

# Or with authentication
export REDIS_URL="redis://:password@redis-server:6379/0"
```

Phlow will automatically detect and use Redis when available.

### Redis Deployment Options

#### 1. Local Redis
```bash
# Start Redis locally
docker run -d -p 6379:6379 redis:alpine

# Configure Phlow
export REDIS_URL="redis://localhost:6379/0"
```

#### 2. Redis Cloud
```bash
# Use Redis Cloud connection string
export REDIS_URL="redis://:password@redis-cloud-endpoint:16379/0"
```

#### 3. AWS ElastiCache
```bash
# Use ElastiCache endpoint
export REDIS_URL="redis://my-cache-cluster.abc123.cache.amazonaws.com:6379/0"
```

## Rate Limit Configuration

### Default Limits

| Operation | Limit | Window | Identifier |
|-----------|-------|--------|------------|
| Authentication | 60/min | 1 minute | Token hash |
| Role Requests | 10/min | 1 minute | Agent ID |

### Custom Rate Limiters

Create custom rate limiters for your endpoints:

```python
from phlow.distributed_rate_limiter import DistributedRateLimiter

# Create a custom rate limiter
api_limiter = DistributedRateLimiter(
    max_requests=100,      # 100 requests
    window_ms=60_000,      # per minute
    redis_url=os.getenv("REDIS_URL")
)

# Use in your endpoint
@app.post("/api/generate")
async def generate(request: Request):
    # Rate limit by IP address
    client_ip = request.client.host
    api_limiter.check_and_raise(client_ip)

    # Process request...
```

## How It Works

### Sliding Window Algorithm

The rate limiter uses a sliding window algorithm for accurate counting:

1. Each request is timestamped and stored
2. Old requests outside the window are removed
3. Current window requests are counted
4. New request is allowed if under limit

This provides smooth rate limiting without sudden resets.

### Redis Implementation

When Redis is available:
- Uses sorted sets for efficient storage
- Atomic operations prevent race conditions
- Automatic key expiration for cleanup
- Handles Redis failures gracefully

### Fallback Behavior

If Redis is unavailable:
- Automatically falls back to in-memory limiting
- Logs warning about degraded functionality
- Continues protecting your service
- No code changes required

## Monitoring

### Rate Limit Headers

Add rate limit headers to responses:

```python
from phlow.distributed_rate_limiter import DistributedRateLimiter

@app.post("/api/endpoint")
async def endpoint(request: Request):
    limiter = DistributedRateLimiter(100, 60_000)

    # Check if allowed
    if not limiter.is_allowed(client_id):
        # Return rate limit headers
        return JSONResponse(
            status_code=429,
            content={"error": "Rate limit exceeded"},
            headers={
                "X-RateLimit-Limit": "100",
                "X-RateLimit-Remaining": "0",
                "X-RateLimit-Reset": str(int(time.time()) + 60)
            }
        )

    # Process request...
```

### Redis Monitoring

Monitor Redis rate limiting:

```bash
# Connect to Redis
redis-cli

# Monitor rate limit keys
KEYS phlow:ratelimit:*

# Check specific rate limit
ZRANGE phlow:ratelimit:auth:abc123 0 -1 WITHSCORES

# Monitor in real-time
MONITOR
```

## Best Practices

1. **Use Redis in Production** - In-memory limiting doesn't work across instances
2. **Set Reasonable Limits** - Balance security with user experience
3. **Monitor Usage** - Track rate limit hits to adjust limits
4. **Use Different Identifiers** - Rate limit by user ID, IP, or API key as appropriate
5. **Handle 429 Responses** - Implement exponential backoff in clients
6. **Configure Redis Persistence** - Ensure rate limits survive Redis restarts

## Troubleshooting

### Redis Connection Failed

If you see "Failed to connect to Redis, falling back to in-memory rate limiting":

1. Check Redis is running: `redis-cli ping`
2. Verify connection string: `redis-cli -u $REDIS_URL ping`
3. Check network/firewall rules
4. Verify Redis version >= 5.0

### Rate Limits Not Working Across Instances

1. Ensure all instances use the same Redis
2. Check Redis connectivity from each instance
3. Verify REDIS_URL is set correctly
4. Monitor Redis keys to confirm usage

### Performance Issues

1. Use Redis connection pooling (automatic)
2. Consider Redis cluster for high load
3. Tune Redis memory settings
4. Use local Redis replicas for read-heavy workloads

## Advanced Usage

### Custom Storage Backend

Implement custom storage for rate limiting:

```python
from phlow.distributed_rate_limiter import RateLimitBackend

class DynamoDBRateLimitBackend(RateLimitBackend):
    def __init__(self, table_name: str):
        self.table = boto3.resource('dynamodb').Table(table_name)

    def is_allowed(self, key: str, max_requests: int, window_ms: int) -> bool:
        # Implement using DynamoDB
        pass

    def reset(self, key: str) -> None:
        # Clear rate limit for key
        pass

# Use custom backend
limiter = DistributedRateLimiter(
    max_requests=100,
    window_ms=60_000,
    backend=DynamoDBRateLimitBackend("rate-limits")
)
```

### Rate Limit Strategies

Different strategies for different use cases:

```python
# Per-user limiting
user_limiter = DistributedRateLimiter(1000, 3600_000)  # 1000/hour
user_limiter.check_and_raise(f"user:{user_id}")

# Per-IP limiting
ip_limiter = DistributedRateLimiter(100, 60_000)  # 100/min
ip_limiter.check_and_raise(f"ip:{client_ip}")

# Per-API key limiting
key_limiter = DistributedRateLimiter(10000, 86400_000)  # 10k/day
key_limiter.check_and_raise(f"key:{api_key}")

# Combined limiting (most restrictive wins)
for limiter, identifier in [
    (user_limiter, f"user:{user_id}"),
    (ip_limiter, f"ip:{client_ip}"),
    (key_limiter, f"key:{api_key}")
]:
    limiter.check_and_raise(identifier)
```
