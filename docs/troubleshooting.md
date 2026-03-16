# Troubleshooting

## Authentication Issues

### "Token must be a non-empty string"

The token passed to `verify_token()` is empty or None. Check that you're extracting the Bearer token correctly:

```python
# The token is the part after "Bearer "
auth_header = request.headers.get("authorization", "")
token = auth_header.removeprefix("Bearer ").strip()
```

### "Token has expired"

JWT tokens have a limited lifetime (default: 1 hour). Generate a fresh token:

```bash
phlow generate-token --key YOUR_SECRET --agent-id my-agent
```

For testing, use a longer expiry:

```python
auth = PhlowAuth(private_key="secret", token_expiry_hours=24.0)
```

### "Invalid token signature"

The token was signed with a different key than the one used for verification. Ensure both sides use the same secret (HS256) or matching key pair (RS256).

```python
# Decode without verification to inspect the token
from phlow import decode_token
claims = decode_token(token)
print(claims)  # Check sub, iss, exp to debug
```

### "No key configured for token verification"

PhlowMiddleware was created with an empty `private_key`. Check your config:

```python
config = PhlowConfig(
    private_key=os.getenv("PRIVATE_KEY"),  # Is this set?
    ...
)
```

## Supabase Connection Issues

### "Supabase URL and anon key are required"

`PhlowMiddleware` requires Supabase credentials. If you just need JWT auth without Supabase, use `PhlowAuth` instead:

```python
from phlow import PhlowAuth

auth = PhlowAuth(private_key="your-secret")
```

### RLS Policy Violations

If you get `PostgrestAPIError: new row violates row-level security policy`:

1. Apply the database schema with proper RLS policies
2. For admin operations, use the Supabase service role key

```python
from phlow.supabase_helpers import SupabaseHelpers
sql = SupabaseHelpers.generate_rls_policy("my_table", "my_policy")
# Run this SQL in your Supabase SQL editor
```

## Rate Limiting

### "Rate limit exceeded"

Default limits: 60 auth requests per minute per token hash.

Configure higher limits:

```python
from phlow.types import RateLimitConfigs

config = PhlowConfig(
    rate_limit_configs=RateLimitConfigs(
        auth_max_requests=120,
        auth_window_ms=60_000,
    ),
    ...
)
```

Reset rate limits programmatically:

```python
middleware.auth_rate_limiter.reset("identifier")
```

## Circuit Breaker Issues

### "Circuit breaker is OPEN"

External dependencies (Supabase, DID resolution) are failing repeatedly. The circuit breaker prevents cascading failures.

Check circuit breaker status:

```python
print(middleware.supabase_circuit_breaker.stats)
# {'state': 'open', 'failure_count': 5, ...}
```

The circuit breaker will automatically try recovery after its timeout period (default: 30-60 seconds).

## Development Issues

### Import Errors

```bash
# Check phlow is installed
python -c "from phlow import PhlowAuth; print('OK')"

# Install with extras
uv add "phlow[fastapi]"    # For FastAPI integration
uv add "phlow[monitoring]"  # For Prometheus metrics
```

### Testing Without Supabase

Use `PhlowAuth` for unit tests — no mocking needed:

```python
from phlow import PhlowAuth

auth = PhlowAuth(private_key="test-secret")
token = auth.create_token(agent_id="test-agent")
claims = auth.verify(token)
assert claims["sub"] == "test-agent"
```

### Debug Logging

```python
from phlow.monitoring.logger import configure_logging
configure_logging(log_level="DEBUG")
```

## Getting Help

Check [GitHub Issues](https://github.com/prassanna-ravishankar/phlow/issues) or create a new issue with:

1. Phlow version: `python -c "import phlow; print(phlow.__version__)"`
2. Python version: `python --version`
3. Complete error traceback
4. Minimal reproduction code
