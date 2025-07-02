# Troubleshooting Guide

This guide helps diagnose and resolve common issues when developing with or deploying Phlow authentication systems.

## Quick Diagnosis

### Authentication Issues

**Symptom**: `401 Unauthorized` responses

**Common Causes**:
- Invalid JWT token
- Missing or incorrect headers
- Agent not found in registry
- Token expiration

**Quick Check**:
```bash
# Verify token structure
echo "JWT_TOKEN_HERE" | cut -d. -f2 | base64 -d | jq

# Test agent card endpoint
curl http://localhost:3000/.well-known/agent.json

# Check Supabase connection
curl "$SUPABASE_URL/rest/v1/agent_cards?select=agent_id&limit=1" \
  -H "apikey: $SUPABASE_ANON_KEY"
```

### Configuration Issues

**Symptom**: Application fails to start

**Common Causes**:
- Missing environment variables
- Invalid key formats
- Supabase connection issues

**Quick Check**:
```bash
# Verify environment variables
env | grep -E "(SUPABASE|PRIVATE_KEY|PUBLIC_KEY)"

# Test key format
openssl rsa -in <(echo "$PRIVATE_KEY") -check -noout
openssl rsa -in <(echo "$PUBLIC_KEY") -pubin -text -noout
```

## JWT Token Issues

### Invalid Token Signature

**Error Messages**:
- `JsonWebTokenError: invalid signature`
- `TokenError: Token verification failed`
- `invalid token`

**Diagnosis Steps**:

1. **Verify Key Pair Match**:
```bash
# Generate test message
echo "test message" > test.txt

# Sign with private key
openssl dgst -sha256 -sign <(echo "$PRIVATE_KEY") test.txt > signature.bin

# Verify with public key
openssl dgst -sha256 -verify <(echo "$PUBLIC_KEY") -signature signature.bin test.txt
```

2. **Check Token Structure**:
```typescript
// JavaScript debugging
import jwt from 'jsonwebtoken'

const token = "YOUR_TOKEN_HERE"
const decoded = jwt.decode(token, { complete: true })
console.log('Header:', decoded.header)
console.log('Payload:', decoded.payload)
```

```python
# Python debugging
import jwt

token = "YOUR_TOKEN_HERE"
decoded = jwt.decode(token, options={"verify_signature": False})
print("Payload:", decoded)
```

3. **Test with Known Good Keys**:
```bash
# Generate fresh key pair for testing
openssl genrsa -out test_private.pem 2048
openssl rsa -in test_private.pem -pubout -out test_public.pem

# Test with these keys
export TEST_PRIVATE_KEY=$(cat test_private.pem)
export TEST_PUBLIC_KEY=$(cat test_public.pem)
```

**Common Solutions**:
- Ensure private and public keys are from the same pair
- Check key format (PEM with proper headers/footers)
- Verify keys are not corrupted during environment variable setting
- Ensure consistent key algorithms (RSA vs ECDSA)

### Token Expiration

**Error Messages**:
- `TokenExpiredError: jwt expired`
- `TokenError: Token has expired`

**Diagnosis**:
```typescript
// Check token expiration
import jwt from 'jsonwebtoken'

const token = "YOUR_TOKEN_HERE"
const decoded = jwt.decode(token) as any

console.log('Issued at:', new Date(decoded.iat * 1000))
console.log('Expires at:', new Date(decoded.exp * 1000))
console.log('Current time:', new Date())
console.log('Time remaining:', decoded.exp - Math.floor(Date.now() / 1000), 'seconds')
```

**Solutions**:
- Increase token expiry time for development: `tokenExpiry: '24h'`
- Implement token refresh logic for production
- Check system clock synchronization between agents
- Handle token expiration gracefully in application logic

### Malformed Tokens

**Error Messages**:
- `JsonWebTokenError: jwt malformed`
- `Invalid token format`

**Common Causes**:
- Missing `Bearer ` prefix in Authorization header
- Token truncation during transmission
- Incorrect base64 encoding

**Debugging**:
```bash
# Check token format (should have 3 parts separated by dots)
echo "YOUR_TOKEN" | tr '.' '\n' | wc -l  # Should output 3

# Validate base64 encoding of each part
echo "HEADER_PART" | base64 -d
echo "PAYLOAD_PART" | base64 -d
```

## Supabase Connection Issues

### Authentication Failures

**Error Messages**:
- `Invalid API key`
- `PGRST301: JWT expired`
- `Connection refused`

**Diagnosis Steps**:

1. **Test Basic Connection**:
```bash
# Test Supabase REST API
curl "$SUPABASE_URL/rest/v1/agent_cards?select=count" \
  -H "apikey: $SUPABASE_ANON_KEY" \
  -H "Authorization: Bearer $SUPABASE_ANON_KEY"
```

2. **Verify Environment Variables**:
```typescript
// Check URL format
const url = process.env.SUPABASE_URL
console.log('URL format valid:', /^https:\/\/[a-z]+\.supabase\.co$/.test(url))

// Check key format
const key = process.env.SUPABASE_ANON_KEY
console.log('Key length:', key.length) // Should be ~152 characters
```

3. **Test with Supabase CLI**:
```bash
# Install Supabase CLI
npm install -g @supabase/cli

# Test connection
supabase db inspect --db-url="postgresql://postgres:password@db.project.supabase.co:5432/postgres"
```

**Common Solutions**:
- Verify project URL format: `https://your-project.supabase.co`
- Ensure anon key is not the service role key
- Check if project is paused (Supabase free tier)
- Verify network connectivity and firewall rules

### Row Level Security Issues

**Error Messages**:
- `PGRST116: The result contains 0 rows`
- `Permission denied`
- `RLS policy violation`

**Diagnosis**:
```sql
-- Check if RLS is enabled
SELECT tablename, rowsecurity 
FROM pg_tables 
WHERE tablename = 'agent_cards';

-- List RLS policies
SELECT schemaname, tablename, policyname, permissive, roles, cmd, qual
FROM pg_policies 
WHERE tablename = 'agent_cards';

-- Test query with RLS disabled (for debugging only)
SET row_security = off;
SELECT * FROM agent_cards LIMIT 5;
SET row_security = on;
```

**Testing RLS Policies**:
```sql
-- Test with specific JWT context
SELECT set_config('request.jwt.claims', '{"sub": "test-agent", "permissions": ["read:data"]}', true);
SELECT * FROM agent_cards WHERE agent_id = 'test-agent';
```

**Solutions**:
- Verify RLS policies allow your use case
- Check JWT claims format in policies
- Ensure agent_id exists in registry for auth policies
- Test with simplified policies first

### Database Performance Issues

**Symptoms**:
- Slow agent card lookups
- Timeout errors during peak load
- High CPU usage on database

**Diagnosis Tools**:
```sql
-- Check slow queries
SELECT query, mean_time, calls, total_time
FROM pg_stat_statements
WHERE query LIKE '%agent_cards%'
ORDER BY mean_time DESC
LIMIT 10;

-- Check index usage
SELECT indexname, idx_scan, idx_tup_read, idx_tup_fetch
FROM pg_stat_user_indexes
WHERE tablename = 'agent_cards';

-- Monitor connection usage
SELECT count(*) as active_connections
FROM pg_stat_activity
WHERE state = 'active';
```

**Performance Solutions**:
```sql
-- Add missing indexes
CREATE INDEX CONCURRENTLY idx_agent_cards_skills_gin 
ON agent_cards USING GIN (skills);

-- Optimize queries
EXPLAIN ANALYZE SELECT * FROM agent_cards WHERE skills @> '[{"name": "data-analysis"}]';

-- Connection pooling
-- Use pgbouncer or Supabase's built-in pooling
```

## Network and Connectivity

### Agent-to-Agent Communication Failures

**Error Messages**:
- `ECONNREFUSED: Connection refused`
- `ETIMEDOUT: Connection timeout`
- `Network request failed`

**Diagnosis Steps**:

1. **Test Basic Connectivity**:
```bash
# Test HTTP connectivity
curl -v http://target-agent.com/.well-known/agent.json

# Test with timeout
curl --max-time 10 http://target-agent.com/health

# Check DNS resolution
nslookup target-agent.com
```

2. **Verify Agent Endpoints**:
```bash
# Check if agent is responding
curl -I http://target-agent.com

# Test discovery endpoint
curl http://target-agent.com/.well-known/agent.json | jq
```

3. **Network Debugging**:
```bash
# Trace network path
traceroute target-agent.com

# Check local firewall
sudo ufw status

# Monitor network traffic
sudo netstat -tulpn | grep :3000
```

**Common Solutions**:
- Verify target agent is running and accessible
- Check firewall rules and security groups
- Ensure correct port and protocol (HTTP vs HTTPS)
- Validate service discovery configuration
- Check load balancer and proxy settings

### SSL/TLS Issues

**Error Messages**:
- `SSL certificate problem`
- `CERT_UNTRUSTED`
- `TLS handshake failed`

**Diagnosis**:
```bash
# Test SSL certificate
openssl s_client -connect target-agent.com:443 -servername target-agent.com

# Check certificate details
curl -vI https://target-agent.com 2>&1 | grep -E "(SSL|TLS|certificate)"

# Test with curl ignoring certificate issues (debugging only)
curl -k https://target-agent.com/.well-known/agent.json
```

**Solutions**:
- Ensure SSL certificates are valid and not expired
- Add CA certificates to trust store if using custom CAs
- For development, use HTTP or self-signed certificates with proper flags
- Verify certificate subject alternative names (SAN)

## Configuration Problems

### Environment Variable Issues

**Common Problems**:
- Variables not loaded
- Incorrect variable names
- Special characters in values

**Debugging**:
```bash
# List all environment variables
printenv | sort

# Check specific variables
echo "SUPABASE_URL: ${SUPABASE_URL}"
echo "Private key length: ${#PRIVATE_KEY}"

# Test variable parsing
node -e "console.log('URL:', process.env.SUPABASE_URL)"
python -c "import os; print('URL:', os.getenv('SUPABASE_URL'))"
```

**Solutions**:
```bash
# Use .env file for development
cat > .env << EOF
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=your-anon-key
PRIVATE_KEY="-----BEGIN RSA PRIVATE KEY-----
MIIEpAIBAAKCAQEA...
-----END RSA PRIVATE KEY-----"
PUBLIC_KEY="-----BEGIN PUBLIC KEY-----
MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEA...
-----END PUBLIC KEY-----"
EOF

# Load in Node.js
require('dotenv').config()

# Load in Python
from dotenv import load_dotenv
load_dotenv()
```

### Key Format Issues

**Error Messages**:
- `Invalid private key format`
- `Error loading key`
- `PEM routines: no start line`

**Validation**:
```bash
# Check private key format
echo "$PRIVATE_KEY" | openssl rsa -check -noout

# Check public key format  
echo "$PUBLIC_KEY" | openssl rsa -pubin -text -noout

# Verify key headers
echo "$PRIVATE_KEY" | head -1  # Should be -----BEGIN RSA PRIVATE KEY-----
echo "$PUBLIC_KEY" | head -1   # Should be -----BEGIN PUBLIC KEY-----
```

**Common Fixes**:
```bash
# Remove extra whitespace
export PRIVATE_KEY=$(echo "$PRIVATE_KEY" | sed '/^$/d')

# Convert PKCS#1 to PKCS#8 if needed
openssl pkcs8 -topk8 -inform PEM -outform PEM -nocrypt \
  -in private_key.pem -out private_key_pkcs8.pem

# Ensure proper line endings (Unix format)
dos2unix private_key.pem
```

## Application-Specific Issues

### Express.js Middleware Problems

**Common Issues**:
- Middleware not applying to routes
- Request object not populated
- Headers not extracted correctly

**Debugging**:
```typescript
// Add debug logging
app.use((req, res, next) => {
  console.log('Headers:', req.headers)
  console.log('Method:', req.method)
  console.log('URL:', req.url)
  next()
})

// Test middleware order
app.use(express.json()) // Ensure this comes before Phlow middleware
app.use('/api', phlow.authenticate())

// Check req.phlow population
app.post('/debug', phlow.authenticate(), (req, res) => {
  console.log('Phlow context:', req.phlow)
  res.json({ context: req.phlow })
})
```

### FastAPI Integration Issues

**Common Problems**:
- Dependency injection not working
- Headers not accessible
- Async/sync mismatch

**Debugging**:
```python
# Add debug middleware
@app.middleware("http")
async def debug_middleware(request: Request, call_next):
    print(f"Headers: {dict(request.headers)}")
    print(f"Method: {request.method}")
    print(f"URL: {request.url}")
    response = await call_next(request)
    return response

# Test dependency
@app.get("/debug")
async def debug_auth(context: PhlowContext = Depends(auth_required)):
    return {
        "agent": context.agent.dict(),
        "claims": context.claims
    }

# Check async context
import asyncio
print(f"Event loop: {asyncio.get_event_loop()}")
```

### Rate Limiting Issues

**Symptoms**:
- Unexpected rate limit errors
- Rate limits not enforcing
- Memory leaks in rate limiter

**Debugging**:
```typescript
// Log rate limiting decisions
const rateLimiter = new RateLimiter({
  maxRequests: 100,
  windowSeconds: 3600,
  debug: true  // Enable debug logging
})

// Check rate limit state
app.get('/debug/rate-limit/:agentId', (req, res) => {
  const remaining = rateLimiter.getRemaining(req.params.agentId)
  res.json({ remaining, window: rateLimiter.getWindow() })
})
```

```python
# Python rate limiter debugging
import logging
logging.getLogger('phlow.rate_limiter').setLevel(logging.DEBUG)

# Monitor memory usage
import psutil
process = psutil.Process()
print(f"Memory usage: {process.memory_info().rss / 1024 / 1024:.2f} MB")
```

## Development Environment Issues

### Local Development Problems

**Docker Issues**:
```bash
# Check container status
docker ps -a

# View container logs
docker logs phlow-agent-1

# Inspect container
docker exec -it phlow-agent-1 /bin/bash

# Check network connectivity between containers
docker network ls
docker network inspect phlow_default
```

**Port Conflicts**:
```bash
# Check port usage
lsof -i :3000
netstat -tulpn | grep :3000

# Kill process using port
sudo fuser -k 3000/tcp
```

**Database Connection in Development**:
```bash
# Test local Supabase
curl http://localhost:54321/rest/v1/agent_cards?select=count \
  -H "apikey: $(cat supabase/.env | grep ANON_KEY | cut -d= -f2)"

# Reset local database
supabase db reset

# Check database logs
supabase logs
```

### Build and Dependencies

**Package Installation Issues**:
```bash
# Clear npm cache
npm cache clean --force
rm -rf node_modules package-lock.json
npm install

# Python dependency issues
pip cache purge
pip install --force-reinstall -r requirements.txt

# Check for version conflicts
npm ls
pip list --outdated
```

**TypeScript Compilation Errors**:
```bash
# Check TypeScript version
npx tsc --version

# Validate tsconfig.json
npx tsc --noEmit

# Check for type conflicts
npm ls @types/node
```

## Monitoring and Debugging

### Application Monitoring

**Health Check Endpoint**:
```typescript
app.get('/health', async (req, res) => {
  try {
    // Test Supabase connection
    const { data, error } = await supabase
      .from('agent_cards')
      .select('count')
      .limit(1)
    
    if (error) throw error
    
    res.json({
      status: 'healthy',
      timestamp: new Date().toISOString(),
      database: 'connected',
      version: process.env.npm_package_version
    })
  } catch (error) {
    res.status(503).json({
      status: 'unhealthy',
      error: error.message,
      timestamp: new Date().toISOString()
    })
  }
})
```

**Structured Logging**:
```typescript
import winston from 'winston'

const logger = winston.createLogger({
  level: process.env.LOG_LEVEL || 'info',
  format: winston.format.combine(
    winston.format.timestamp(),
    winston.format.errors({ stack: true }),
    winston.format.json()
  ),
  transports: [
    new winston.transports.File({ filename: 'error.log', level: 'error' }),
    new winston.transports.File({ filename: 'combined.log' }),
    new winston.transports.Console()
  ]
})

// Use in middleware
app.use((req, res, next) => {
  logger.info('Request received', {
    method: req.method,
    url: req.url,
    userAgent: req.get('User-Agent'),
    agentId: req.get('x-phlow-agent-id')
  })
  next()
})
```

### Performance Monitoring

**Metrics Collection**:
```typescript
import { performance } from 'perf_hooks'

// Measure authentication time
const authTimer = performance.now()
await middleware.authenticate(token, agentId)
const authTime = performance.now() - authTimer

logger.info('Authentication completed', {
  duration: authTime,
  agentId,
  success: true
})
```

**Memory Monitoring**:
```typescript
// Monitor memory usage
setInterval(() => {
  const usage = process.memoryUsage()
  logger.info('Memory usage', {
    rss: Math.round(usage.rss / 1024 / 1024),
    heapTotal: Math.round(usage.heapTotal / 1024 / 1024),
    heapUsed: Math.round(usage.heapUsed / 1024 / 1024),
    external: Math.round(usage.external / 1024 / 1024)
  })
}, 60000) // Every minute
```

## Getting Help

### Debug Information Collection

When reporting issues, include:

```bash
# System information
cat > debug-info.txt << EOF
Node.js version: $(node --version)
Python version: $(python --version)
npm version: $(npm --version)
OS: $(uname -a)
Date: $(date)

Environment variables:
SUPABASE_URL: ${SUPABASE_URL}
PUBLIC_KEY length: ${#PUBLIC_KEY}
PRIVATE_KEY length: ${#PRIVATE_KEY}

Package versions:
$(npm ls phlow-auth 2>/dev/null || echo "phlow-auth not installed")
$(pip show phlow-auth 2>/dev/null || echo "phlow-auth not installed")
EOF
```

### Log Analysis

**Common Log Patterns**:
```bash
# Authentication failures
grep -E "(401|Unauthorized|Authentication failed)" logs/app.log

# Token errors
grep -E "(TokenError|jwt|signature)" logs/app.log

# Database issues
grep -E "(Supabase|PGRST|database)" logs/app.log

# Performance issues
grep -E "(timeout|slow|performance)" logs/app.log
```

### Community Resources

- **GitHub Issues**: [phlow/issues](https://github.com/prassanna-ravishankar/phlow/issues)
- **Documentation**: [docs/dev-guide](../dev-guide/)
- **Examples**: [examples/](../../examples/)

### Emergency Procedures

**Service Recovery**:
```bash
# Restart with minimal configuration
export PHLOW_DEBUG=true
export PHLOW_LOG_LEVEL=debug
npm start

# Bypass authentication (emergency only)
export PHLOW_BYPASS_AUTH=true  # Never use in production!
```

**Data Recovery**:
```sql
-- Backup agent cards before making changes
CREATE TABLE agent_cards_backup AS SELECT * FROM agent_cards;

-- Restore from backup if needed
TRUNCATE agent_cards;
INSERT INTO agent_cards SELECT * FROM agent_cards_backup;
```

---

This troubleshooting guide provides systematic approaches to diagnosing and resolving common Phlow authentication issues. For additional help, check the [Development Guide](local-development.md) or reach out to the community.