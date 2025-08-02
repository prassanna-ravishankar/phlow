# Production Deployment Guide

This guide covers deploying Phlow-powered agents in production environments with security, performance, and reliability best practices.

## Prerequisites

- **Python 3.10+** in production environment
- **PostgreSQL database** (Supabase or self-hosted)
- **Redis instance** for distributed rate limiting (recommended)
- **TLS certificates** for HTTPS endpoints
- **Monitoring infrastructure** (Prometheus/Grafana recommended)

## Security Checklist

### 1. Key Management

**❌ Never do this in production:**
```bash
# Don't store keys in plain text files
export PRIVATE_KEY="-----BEGIN RSA PRIVATE KEY-----..."
```

**✅ Use secure key management:**

```bash
# Option 1: Environment variables from secure vault
export PRIVATE_KEY=$(vault kv get -field=private_key secret/phlow/keys)

# Option 2: Use Phlow's encrypted key store
from phlow.security import EncryptedFileKeyStore
key_store = EncryptedFileKeyStore("/secure/keys", master_key=os.environ["MASTER_KEY"])
```

### 2. Database Security

**Apply Row Level Security (RLS) policies:**
```sql
-- Enable RLS on all Phlow tables
ALTER TABLE agents ENABLE ROW LEVEL SECURITY;
ALTER TABLE agent_audit_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE rate_limit_counters ENABLE ROW LEVEL SECURITY;

-- Apply the provided policies
\i docs/database-schema.sql
```

**Use service role key for admin operations only:**
```python
# Regular operations - use anon key
config = PhlowConfig(
    supabase_url=os.environ["SUPABASE_URL"],
    supabase_anon_key=os.environ["SUPABASE_ANON_KEY"]  # Public key
)

# Admin operations - use service role
admin_client = create_client(
    os.environ["SUPABASE_URL"],
    os.environ["SUPABASE_SERVICE_ROLE_KEY"]  # Secret key
)
```

### 3. Network Security

**Configure proper CORS:**
```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://trusted-domain.com"],  # Specific origins
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["Authorization", "X-Agent-ID"],
)
```

**Use HTTPS only:**
```python
from fastapi.middleware.httpsredirect import HTTPSRedirectMiddleware

# Redirect HTTP to HTTPS
app.add_middleware(HTTPSRedirectMiddleware)
```

## Performance Configuration

### 1. Rate Limiting

**Configure Redis for distributed rate limiting:**
```python
from phlow.types import RateLimitConfig

rate_config = RateLimitConfig(
    requests_per_minute=1000,  # Adjust for your needs
    burst_size=50,
    redis_url="redis://redis-cluster:6379/0",
    redis_password=os.environ["REDIS_PASSWORD"]
)

config = PhlowConfig(
    # ... other config
    rate_limiting=rate_config
)
```

### 2. Circuit Breakers

**Configure circuit breakers for external dependencies:**
```python
from phlow.monitoring import configure_circuit_breaker

# Configure circuit breaker for Supabase
configure_circuit_breaker(
    name="supabase",
    failure_threshold=5,
    timeout_seconds=30,
    recovery_timeout=300
)

# Configure circuit breaker for DID resolution
configure_circuit_breaker(
    name="did_resolver",
    failure_threshold=3,
    timeout_seconds=10,
    recovery_timeout=60
)
```

### 3. Connection Pooling

**Configure database connection pooling:**
```python
from supabase import create_client, ClientOptions

# Configure connection pool
client_options = ClientOptions(
    postgrest_client_timeout=10,
    storage_client_timeout=10,
    schema="public"
)

supabase = create_client(
    supabase_url,
    supabase_key,
    options=client_options
)
```

## Monitoring Setup

### 1. Structured Logging

```python
from phlow.monitoring import configure_logging

# Configure structured logging for production
configure_logging(
    level="INFO",
    format="json",
    output="/var/log/phlow/agent.log"
)
```

### 2. Prometheus Metrics

```python
from phlow.monitoring import enable_prometheus_metrics

# Enable Prometheus metrics endpoint
enable_prometheus_metrics(
    port=9090,
    endpoint="/metrics"
)
```

**Key metrics to monitor:**
- `phlow_auth_requests_total` - Authentication attempts
- `phlow_auth_duration_seconds` - Authentication latency
- `phlow_rate_limit_hits_total` - Rate limit violations
- `phlow_circuit_breaker_state` - Circuit breaker status
- `phlow_supabase_connections` - Database connections

### 3. Health Checks

```python
@app.get("/health")
async def health_check():
    """Production health check endpoint"""
    checks = {}

    try:
        # Check Supabase connectivity
        response = supabase.table('agents').select('agent_id').limit(1).execute()
        checks["supabase"] = "healthy"
    except Exception as e:
        checks["supabase"] = f"unhealthy: {str(e)}"

    try:
        # Check Redis connectivity (if used)
        import redis
        r = redis.from_url(os.environ["REDIS_URL"])
        r.ping()
        checks["redis"] = "healthy"
    except Exception as e:
        checks["redis"] = f"unhealthy: {str(e)}"

    # Check circuit breaker status
    from phlow.monitoring import get_circuit_breaker_status
    checks["circuit_breakers"] = get_circuit_breaker_status()

    overall_status = "healthy" if all(
        status == "healthy" for status in checks.values()
        if isinstance(status, str)
    ) else "unhealthy"

    return {
        "status": overall_status,
        "timestamp": datetime.utcnow().isoformat(),
        "checks": checks
    }
```

## Deployment Configurations

### 1. Docker Deployment

**Dockerfile:**
```dockerfile
FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    openssl \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN useradd -m -u 1000 phlow

# Set working directory
WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY --chown=phlow:phlow . .

# Switch to non-root user
USER phlow

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Start application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

**docker-compose.yml:**
```yaml
version: '3.8'

services:
  phlow-agent:
    build: .
    ports:
      - "8000:8000"
    environment:
      - SUPABASE_URL=${SUPABASE_URL}
      - SUPABASE_ANON_KEY=${SUPABASE_ANON_KEY}
      - PRIVATE_KEY=${PRIVATE_KEY}
      - REDIS_URL=redis://redis:6379
    depends_on:
      - redis
    restart: unless-stopped

  redis:
    image: redis:7-alpine
    restart: unless-stopped
    volumes:
      - redis_data:/data

  prometheus:
    image: prom/prometheus
    ports:
      - "9090:9090"
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml

volumes:
  redis_data:
```

### 2. Kubernetes Deployment

**deployment.yaml:**
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: phlow-agent
spec:
  replicas: 3
  selector:
    matchLabels:
      app: phlow-agent
  template:
    metadata:
      labels:
        app: phlow-agent
    spec:
      containers:
      - name: phlow-agent
        image: your-registry/phlow-agent:latest
        ports:
        - containerPort: 8000
        env:
        - name: SUPABASE_URL
          valueFrom:
            secretKeyRef:
              name: phlow-secrets
              key: supabase-url
        - name: SUPABASE_ANON_KEY
          valueFrom:
            secretKeyRef:
              name: phlow-secrets
              key: supabase-anon-key
        - name: PRIVATE_KEY
          valueFrom:
            secretKeyRef:
              name: phlow-secrets
              key: private-key
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 5
        resources:
          requests:
            memory: "256Mi"
            cpu: "250m"
          limits:
            memory: "512Mi"
            cpu: "500m"
```

### 3. Cloud Provider Specific

**AWS ECS with Fargate:**
```json
{
  "family": "phlow-agent",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "512",
  "memory": "1024",
  "executionRoleArn": "arn:aws:iam::ACCOUNT:role/ecsTaskExecutionRole",
  "containerDefinitions": [
    {
      "name": "phlow-agent",
      "image": "your-account.dkr.ecr.region.amazonaws.com/phlow-agent:latest",
      "portMappings": [
        {
          "containerPort": 8000,
          "protocol": "tcp"
        }
      ],
      "environment": [
        {
          "name": "SUPABASE_URL",
          "value": "https://your-project.supabase.co"
        }
      ],
      "secrets": [
        {
          "name": "PRIVATE_KEY",
          "valueFrom": "arn:aws:secretsmanager:region:account:secret:phlow/private-key"
        }
      ],
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/phlow-agent",
          "awslogs-region": "us-west-2",
          "awslogs-stream-prefix": "ecs"
        }
      }
    }
  ]
}
```

## Environment-Specific Configurations

### Development
```python
config = PhlowConfig(
    # ... basic config
    enable_audit_logging=True,
    rate_limiting=RateLimitConfig(requests_per_minute=60),
    log_level="DEBUG"
)
```

### Staging
```python
config = PhlowConfig(
    # ... basic config
    enable_audit_logging=True,
    rate_limiting=RateLimitConfig(
        requests_per_minute=500,
        redis_url="redis://staging-redis:6379"
    ),
    log_level="INFO"
)
```

### Production
```python
config = PhlowConfig(
    # ... basic config
    enable_audit_logging=True,
    rate_limiting=RateLimitConfig(
        requests_per_minute=2000,
        burst_size=100,
        redis_url="redis://prod-redis-cluster:6379",
        redis_password=os.environ["REDIS_PASSWORD"]
    ),
    circuit_breakers=CircuitBreakerConfig(
        supabase_failure_threshold=10,
        did_resolver_failure_threshold=5
    ),
    log_level="WARN"
)
```

## Performance Tuning

### 1. Database Optimization

```sql
-- Create indexes for common queries
CREATE INDEX CONCURRENTLY idx_agents_agent_id ON agents(agent_id);
CREATE INDEX CONCURRENTLY idx_audit_logs_agent_timestamp ON agent_audit_logs(agent_id, created_at);
CREATE INDEX CONCURRENTLY idx_rate_limits_agent_window ON rate_limit_counters(agent_id, window_start);
```

### 2. Application Tuning

```python
# Configure uvicorn for production
uvicorn.run(
    app,
    host="0.0.0.0",
    port=8000,
    workers=4,  # CPU cores
    access_log=False,  # Use structured logging instead
    server_header=False,
    date_header=False
)
```

### 3. Memory Management

```python
# Configure cache sizes
from phlow.rbac import configure_did_cache

configure_did_cache(
    max_size=10000,  # Adjust based on available memory
    ttl=3600,        # 1 hour cache
    cleanup_interval=300  # 5 minutes
)
```

## Backup and Recovery

### 1. Database Backups

```bash
# Automated Supabase backup
pg_dump "postgresql://postgres:$PASSWORD@db.$PROJECT.supabase.co:5432/postgres" \
  --clean --if-exists --no-owner --no-privileges \
  -f "backup-$(date +%Y%m%d-%H%M%S).sql"
```

### 2. Key Backup

```bash
# Secure key backup
gpg --cipher-algo AES256 --compress-algo 1 --s2k-mode 3 \
  --s2k-digest-algo SHA256 --s2k-count 65536 \
  --symmetric --output keys-backup.gpg keys/
```

## Troubleshooting Production Issues

### Common Production Problems

1. **Memory leaks**: Monitor memory usage and restart containers if needed
2. **Database connection exhaustion**: Use connection pooling and monitoring
3. **Rate limiting too aggressive**: Adjust based on traffic patterns
4. **Circuit breaker false positives**: Tune thresholds based on dependency SLAs

### Debugging Commands

```bash
# Check container logs
docker logs phlow-agent

# Monitor metrics
curl http://localhost:9090/metrics

# Check health
curl http://localhost:8000/health

# Database query performance
EXPLAIN ANALYZE SELECT * FROM agents WHERE agent_id = 'agent-123';
```

## Security Audit Checklist

- [ ] RSA keys stored securely (not in environment variables)
- [ ] Database RLS policies applied
- [ ] TLS/HTTPS enabled
- [ ] CORS properly configured
- [ ] Rate limiting enabled
- [ ] Audit logging enabled
- [ ] Circuit breakers configured
- [ ] Monitoring and alerting set up
- [ ] Backup procedures tested
- [ ] Security headers configured
- [ ] Container running as non-root user
- [ ] Secrets managed through secure vault

---

For additional support, see the [Troubleshooting Guide](troubleshooting.md) or create an issue on [GitHub](https://github.com/prassanna-ravishankar/phlow/issues).
