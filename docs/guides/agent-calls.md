# Making Agent Calls

Connect securely to other A2A Protocol agents.

## Basic Agent Call

### JavaScript
```javascript
// Phlow handles authentication automatically
const response = await phlow.callAgent('https://other-agent.com/api/analyze', {
  data: 'content to analyze',
  options: { format: 'json' }
});

console.log(response.result);
```

### Python
```python
# Same simple interface
response = await phlow.call_agent('https://other-agent.com/api/analyze', {
    'data': 'content to analyze',
    'options': {'format': 'json'}
})

print(response['result'])
```

## Agent Discovery

### Find Agents
```javascript
// Search the Supabase registry
const agents = await phlow.findAgents({
  skills: ['data-analysis'],
  location: 'us-east'
});

for (const agent of agents) {
  console.log(`${agent.name}: ${agent.serviceUrl}`);
}
```

### Get Agent Info
```javascript
// Get full agent card
const agentCard = await phlow.getAgent('agent-id');
console.log('Skills:', agentCard.skills);
console.log('Service URL:', agentCard.serviceUrl);
```

## Advanced Calls

### With Custom Permissions
```javascript
const response = await phlow.callAgent(url, data, {
  permissions: ['read', 'write', 'admin'],
  timeout: 30000  // 30 seconds
});
```

### With Custom Headers
```javascript
const response = await phlow.callAgent(url, data, {
  headers: {
    'Content-Type': 'application/json',
    'X-Custom-Header': 'value'
  }
});
```

### Streaming Responses
```javascript
const stream = await phlow.callAgentStream(url, data);

stream.on('data', (chunk) => {
  console.log('Received:', chunk);
});

stream.on('end', () => {
  console.log('Stream complete');
});
```

## Error Handling

```javascript
try {
  const response = await phlow.callAgent(url, data);
} catch (error) {
  if (error.code === 'AGENT_UNREACHABLE') {
    console.log('Agent is offline or unreachable');
  } else if (error.code === 'AUTHENTICATION_FAILED') {
    console.log('Agent rejected our credentials');
  } else if (error.code === 'PERMISSION_DENIED') {
    console.log('Insufficient permissions for this request');
  } else {
    console.log('Other error:', error.message);
  }
}
```

## Agent Registry

### Register Your Agent
```javascript
// Register in Supabase for discovery
await phlow.registerAgent({
  agentId: 'my-agent-001',
  name: 'My Analysis Agent',
  skills: ['data-analysis', 'visualization'],
  serviceUrl: 'https://my-agent.com',
  metadata: {
    version: '1.0.0',
    region: 'us-east-1'
  }
});
```

### Update Agent Info
```javascript
await phlow.updateAgent('my-agent-001', {
  skills: ['data-analysis', 'ml-training'],  // Updated skills
  status: 'online'
});
```

### Deregister Agent
```javascript
await phlow.deregisterAgent('my-agent-001');
```

## Monitoring Calls

### Call Metrics
```javascript
// Enable call tracking
const phlow = new PhlowMiddleware({
  // ... config
  enableCallMetrics: true
});

// View metrics
const metrics = await phlow.getCallMetrics();
console.log('Total calls:', metrics.totalCalls);
console.log('Average response time:', metrics.avgResponseTime);
```

### Failed Calls
```javascript
// Get failed call history
const failedCalls = await phlow.getFailedCalls({
  agentId: 'problematic-agent',
  since: '2024-01-01'
});
```

## Best Practices

### Connection Pooling
```javascript
// Reuse connections for better performance
const phlow = new PhlowMiddleware({
  // ... config
  connectionPool: {
    maxConnections: 10,
    keepAlive: true
  }
});
```

### Timeout Configuration
```javascript
// Set reasonable timeouts
const response = await phlow.callAgent(url, data, {
  timeout: 10000,      // 10 seconds for most calls
  retryCount: 3,       // Retry failed calls
  retryDelay: 1000     // Wait 1 second between retries
});
```

### Caching Agent Cards
```javascript
// Cache agent discovery for performance
const phlow = new PhlowMiddleware({
  // ... config
  agentCache: {
    enabled: true,
    ttl: 300000  // 5 minutes
  }
});
```

## Next Steps

- [Authentication Guide](authentication.md) - How auth works
- [Security Best Practices](security.md) - Secure agent calls
- [API Reference](../api/javascript.md) - All call options