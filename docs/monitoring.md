# Monitoring and Observability Guide

Phlow provides comprehensive monitoring and observability features to help you understand your agent's performance, security posture, and operational health.

## Overview

The monitoring system includes:
- **Structured Logging** - JSON-formatted logs with request tracing
- **Metrics Collection** - Prometheus-compatible metrics for monitoring
- **Request Tracing** - Track requests across distributed systems
- **Security Events** - Authentication and authorization monitoring
- **Performance Metrics** - Response times and throughput tracking

## Quick Setup

### Install Monitoring Dependencies

```bash
# Install monitoring features
pip install "phlow[monitoring]"

# Or install specific dependencies
pip install structlog prometheus-client
```

### Basic Configuration

```python
from phlow.monitoring import configure_logging, configure_metrics

# Configure structured logging
logger = configure_logging(
    log_level="INFO",
    output_format="json",  # or "console" for development
    enable_metrics=True,
    enable_tracing=True
)

# Configure metrics collection
metrics = configure_metrics(enable_prometheus=True)
```

## Structured Logging

### Configuration

```python
from phlow.monitoring import configure_logging

# Development configuration (human-readable)
logger = configure_logging(
    log_level="DEBUG",
    output_format="console",
    enable_metrics=True,
    enable_tracing=True
)

# Production configuration (JSON output)
logger = configure_logging(
    log_level="INFO",
    output_format="json",
    enable_metrics=True,
    enable_tracing=True
)
```

### Log Output Examples

**Console Format (Development):**
```
2025-01-15 10:30:45 [INFO    ] Authentication succeeded [phlow] agent_id=agent-123 request_id=abc-def-123 success=True
```

**JSON Format (Production):**
```json
{
  "timestamp": 1705320645.123,
  "level": "info",
  "logger": "phlow",
  "message": "Authentication succeeded",
  "request_id": "abc-def-123",
  "agent_id": "agent-123",
  "event_type": "authentication",
  "success": true,
  "token_hash": "sha256:abc123..."
}
```

### Manual Logging

```python
from phlow.monitoring import get_logger

logger = get_logger()

# Set request context
logger.set_request_context(
    req_id="request-123",
    ag_id="agent-456"
)

# Log structured events
logger.log_authentication_event(
    agent_id="agent-123",
    success=True,
    token_hash="abc123"
)

logger.log_rate_limit_event(
    identifier="192.168.1.1",
    limit_type="api",
    exceeded=False,
    current_count=45,
    limit=100
)
```

## Metrics Collection

### Prometheus Integration

```python
from phlow.monitoring import configure_metrics

# Enable Prometheus metrics
metrics = configure_metrics(enable_prometheus=True)

# Metrics are automatically collected by Phlow middleware
# Access metrics endpoint in your FastAPI app:

from fastapi import FastAPI
from phlow.monitoring import get_metrics_collector

app = FastAPI()

@app.get("/metrics")
async def metrics():
    collector = get_metrics_collector()
    return Response(
        content=collector.get_metrics_text(),
        media_type="text/plain"
    )
```

### Available Metrics

| Metric | Type | Description | Labels |
|--------|------|-------------|--------|
| `phlow_auth_attempts_total` | Counter | Authentication attempts | `agent_id`, `success` |
| `phlow_auth_duration_seconds` | Histogram | Authentication latency | `agent_id` |
| `phlow_rate_limit_checks_total` | Counter | Rate limit checks | `limit_type`, `exceeded` |
| `phlow_did_resolutions_total` | Counter | DID resolutions | `cached`, `success` |
| `phlow_external_api_calls_total` | Counter | External API calls | `service`, `status_code` |
| `phlow_database_operations_total` | Counter | Database operations | `operation`, `table`, `success` |

### Manual Metrics

```python
from phlow.monitoring import get_metrics_collector, MetricsTimer

collector = get_metrics_collector()

# Record custom metrics
collector.record_auth_attempt("agent-123", True, 0.045)
collector.record_rate_limit_check("api", False)

# Use timing context manager
with MetricsTimer(collector, "external_api", service="supabase"):
    # Make API call
    response = await supabase_client.query()
```

## FastAPI Integration

### Add Logging Middleware

```python
from fastapi import FastAPI
from phlow.monitoring import LoggingMiddleware, get_logger

app = FastAPI()

# Add logging middleware
logger = get_logger()
app.middleware("http")(LoggingMiddleware(logger))

@app.post("/api/agent")
async def agent_endpoint():
    # Request context is automatically set
    logger.info("Processing agent request")
    return {"status": "success"}
```

### Complete Integration Example

```python
from fastapi import FastAPI, Depends, Response
from phlow import PhlowMiddleware, PhlowConfig
from phlow.monitoring import (
    configure_logging,
    configure_metrics,
    LoggingMiddleware,
    get_metrics_collector
)
from phlow.integrations.fastapi import create_phlow_dependency

# Configure monitoring
configure_logging(output_format="json", log_level="INFO")
configure_metrics(enable_prometheus=True)

app = FastAPI()

# Add logging middleware
app.middleware("http")(LoggingMiddleware(get_logger()))

# Configure Phlow
config = PhlowConfig(...)  # Your config
middleware = PhlowMiddleware(config)
auth_required = create_phlow_dependency(middleware)

@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint."""
    collector = get_metrics_collector()
    return Response(
        content=collector.get_metrics_text(),
        media_type="text/plain"
    )

@app.get("/health")
async def health():
    """Health check endpoint."""
    collector = get_metrics_collector()
    metrics_data = collector.get_metrics_dict()

    return {
        "status": "healthy",
        "metrics_summary": {
            "auth_attempts": sum(metrics_data["counters"].values()),
            "active_connections": metrics_data["gauges"].get("active_connections", 0)
        }
    }

@app.post("/api/secure")
async def secure_endpoint(context = Depends(auth_required)):
    # All authentication events are automatically logged
    return {"message": "Success", "agent": context.agent.name}
```

## Log Analysis

### Searching Logs

**Find authentication failures:**
```bash
# Using jq for JSON logs
cat app.log | jq 'select(.event_type == "authentication" and .success == false)'

# Using grep for console logs
grep "Authentication failed" app.log
```

**Track specific agent:**
```bash
cat app.log | jq 'select(.agent_id == "agent-123")'
```

**Rate limit violations:**
```bash
cat app.log | jq 'select(.event_type == "rate_limit" and .exceeded == true)'
```

### Log Aggregation

**ELK Stack Configuration:**
```yaml
# logstash.conf
input {
  file {
    path => "/app/logs/phlow.log"
    codec => json
  }
}

filter {
  if [event_type] {
    mutate {
      add_tag => ["phlow", "%{event_type}"]
    }
  }
}

output {
  elasticsearch {
    hosts => ["elasticsearch:9200"]
    index => "phlow-logs-%{+YYYY.MM.dd}"
  }
}
```

## Prometheus Monitoring

### Grafana Dashboard

Example queries for Grafana:

**Authentication Rate:**
```promql
rate(phlow_auth_attempts_total[5m])
```

**Authentication Success Rate:**
```promql
rate(phlow_auth_attempts_total{success="true"}[5m]) /
rate(phlow_auth_attempts_total[5m])
```

**P95 Authentication Latency:**
```promql
histogram_quantile(0.95, rate(phlow_auth_duration_seconds_bucket[5m]))
```

**Rate Limit Violations:**
```promql
rate(phlow_rate_limit_checks_total{exceeded="true"}[5m])
```

### Alerting Rules

```yaml
# prometheus.rules.yml
groups:
  - name: phlow
    rules:
      - alert: HighAuthFailureRate
        expr: rate(phlow_auth_attempts_total{success="false"}[5m]) > 0.1
        for: 2m
        labels:
          severity: warning
        annotations:
          summary: "High authentication failure rate"
          description: "Authentication failure rate is {{ $value }} per second"

      - alert: RateLimitViolations
        expr: rate(phlow_rate_limit_checks_total{exceeded="true"}[5m]) > 0.05
        for: 1m
        labels:
          severity: warning
        annotations:
          summary: "Rate limit violations detected"

      - alert: HighAuthLatency
        expr: histogram_quantile(0.95, rate(phlow_auth_duration_seconds_bucket[5m])) > 1.0
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High authentication latency"
          description: "P95 auth latency is {{ $value }}s"
```

## Distributed Tracing

### Request Correlation

Phlow automatically generates request IDs for distributed tracing:

```python
from phlow.monitoring import get_logger

logger = get_logger()

# Request ID is automatically generated and included in all logs
# You can also set custom request context:
logger.set_request_context(
    req_id="custom-request-id",
    ag_id="agent-123"
)
```

### Integration with External Systems

**Forward request ID to external services:**
```python
import httpx
from phlow.monitoring import request_id

async def call_external_service():
    req_id = request_id.get()
    headers = {"X-Request-ID": req_id} if req_id else {}

    async with httpx.AsyncClient() as client:
        response = await client.get(
            "https://external-service.com/api",
            headers=headers
        )
    return response
```

## Performance Monitoring

### Response Time Tracking

```python
from phlow.monitoring import MetricsTimer, get_metrics_collector

collector = get_metrics_collector()

# Track operation timing
with MetricsTimer(collector, "did_resolution", cached=False):
    did_document = await resolve_did(did)

# Manual timing
import time
start = time.time()
result = await operation()
duration = time.time() - start
collector.record_external_api_call("service", 200, duration)
```

### Memory and Resource Monitoring

```python
import psutil
from phlow.monitoring import get_metrics_collector

collector = get_metrics_collector()

# Monitor resource usage
def collect_system_metrics():
    process = psutil.Process()

    # Set gauges for current resource usage
    collector.set_active_connections(len(process.connections()))

    # You can extend this with custom gauges
    memory_usage = process.memory_info().rss / 1024 / 1024  # MB
    # collector.set_memory_usage(memory_usage)
```

## Troubleshooting

### Common Issues

**Logs not structured:**
- Ensure `output_format="json"` in configuration
- Check that structlog is installed

**Metrics not appearing:**
- Verify `enable_prometheus=True` in metrics configuration
- Install prometheus-client: `pip install prometheus-client`

**Request IDs missing:**
- Add LoggingMiddleware to your FastAPI app
- Ensure context is set manually if not using middleware

### Debug Logging

Enable debug logging to see internal Phlow operations:

```python
from phlow.monitoring import configure_logging

# Enable debug logging
configure_logging(log_level="DEBUG", output_format="console")
```

## Best Practices

1. **Use JSON format in production** for better log parsing
2. **Set up log rotation** to manage disk space
3. **Monitor authentication patterns** for security insights
4. **Set up alerting** for rate limit violations and auth failures
5. **Use request tracing** to correlate events across services
6. **Monitor performance metrics** to identify bottlenecks
7. **Regularly review logs** for security anomalies
