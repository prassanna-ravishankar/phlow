require('dotenv').config();
const express = require('express');
const { PhlowMiddleware } = require('phlow-auth');

const app = express();
const port = process.env.DATA_AGENT_PORT || 4001;

const dataAgentConfig = {
  agentId: 'data-agent',
  name: 'Data Storage Agent',
  description: 'Handles data storage and retrieval operations',
  permissions: ['read:data', 'write:data', 'manage:datasets'],
  publicKey: process.env.DATA_AGENT_PUBLIC_KEY?.replace(/\\n/g, '\n'),
};

const phlow = new PhlowMiddleware({
  supabaseUrl: process.env.SUPABASE_URL,
  supabaseAnonKey: process.env.SUPABASE_ANON_KEY,
  agentCard: dataAgentConfig,
  privateKey: process.env.DATA_AGENT_PRIVATE_KEY?.replace(/\\n/g, '\n'),
  options: {
    enableAudit: true,
  },
});

app.use(express.json());

// Mock database
const mockDatabase = {
  users: {
    'user-123': {
      id: 'user-123',
      name: 'Alice Johnson',
      email: 'alice@example.com',
      preferences: { theme: 'dark', language: 'en' },
      activity: {
        lastLogin: '2024-01-15T10:30:00Z',
        sessionCount: 42,
        totalActions: 1337,
      },
    },
  },
  datasets: {
    'sales-data': {
      name: 'Sales Data Q4 2023',
      records: [
        { date: '2023-10-01', amount: 1200, region: 'north' },
        { date: '2023-10-02', amount: 950, region: 'south' },
        { date: '2023-10-03', amount: 1800, region: 'east' },
      ],
    },
    'user-metrics': {
      name: 'User Engagement Metrics',
      records: [
        { userId: 'user-123', metric: 'page_views', value: 45 },
        { userId: 'user-123', metric: 'session_duration', value: 1200 },
      ],
    },
  },
  analytics: [],
  processedResults: [],
};

// Public endpoints
app.get('/', (req, res) => {
  res.json({
    message: 'Data Storage Agent',
    agent: dataAgentConfig,
    capabilities: [
      'User data retrieval',
      'Dataset management',
      'Analytics storage',
      'Data validation',
    ],
  });
});

app.get('/health', (req, res) => {
  res.json({
    status: 'healthy',
    timestamp: new Date().toISOString(),
    uptime: process.uptime(),
    database: {
      users: Object.keys(mockDatabase.users).length,
      datasets: Object.keys(mockDatabase.datasets).length,
      analytics: mockDatabase.analytics.length,
    },
  });
});

app.get('/status', phlow.authenticate(), (req, res) => {
  res.json({
    agent: dataAgentConfig.name,
    status: 'operational',
    storage: {
      users: Object.keys(mockDatabase.users).length,
      datasets: Object.keys(mockDatabase.datasets).length,
      analytics: mockDatabase.analytics.length,
      processedResults: mockDatabase.processedResults.length,
    },
    requestedBy: req.phlow.agent.agentId,
    timestamp: new Date().toISOString(),
  });
});

// User-related endpoints
app.get('/users/profile', phlow.authenticate({ requiredPermissions: ['read:data'] }), (req, res) => {
  const userId = req.query.userId || 'user-123';
  const user = mockDatabase.users[userId];
  
  if (!user) {
    return res.status(404).json({
      error: 'User not found',
      userId,
    });
  }

  res.json({
    message: 'User profile retrieved',
    user,
    requestedBy: req.phlow.agent.agentId,
    timestamp: new Date().toISOString(),
  });
});

// Dataset-related endpoints
app.post('/datasets/validate', phlow.authenticate({ requiredPermissions: ['read:data'] }), (req, res) => {
  const { dataset, operation, requesterId } = req.body;
  
  const datasetExists = mockDatabase.datasets[dataset];
  const authorized = req.phlow.claims.permissions.includes('read:data') ||
                    req.phlow.claims.permissions.includes('manage:datasets');
  
  res.json({
    authorized: authorized && datasetExists,
    dataset,
    operation,
    requesterId,
    reason: !datasetExists ? 'Dataset not found' : 
            !authorized ? 'Insufficient permissions' : 'Access granted',
  });
});

app.get('/datasets/:datasetId', phlow.authenticate({ requiredPermissions: ['read:data'] }), (req, res) => {
  const { datasetId } = req.params;
  const dataset = mockDatabase.datasets[datasetId];
  
  if (!dataset) {
    return res.status(404).json({
      error: 'Dataset not found',
      datasetId,
    });
  }

  res.json({
    message: 'Dataset retrieved',
    dataset,
    requestedBy: req.phlow.agent.agentId,
    timestamp: new Date().toISOString(),
  });
});

app.post('/datasets/results', phlow.authenticate({ requiredPermissions: ['write:data'] }), (req, res) => {
  const { originalDataset, processedData, operation, workflowId } = req.body;
  
  const result = {
    id: `result-${Date.now()}`,
    originalDataset,
    processedData,
    operation,
    workflowId,
    processedBy: req.phlow.agent.agentId,
    timestamp: new Date().toISOString(),
  };
  
  mockDatabase.processedResults.push(result);
  
  res.json({
    message: 'Processed results stored successfully',
    success: true,
    resultId: result.id,
    timestamp: new Date().toISOString(),
  });
});

// Analytics storage
app.post('/analytics/store', phlow.authenticate({ requiredPermissions: ['write:data'] }), (req, res) => {
  const { userId, analytics, workflowId } = req.body;
  
  const analyticsRecord = {
    id: `analytics-${Date.now()}`,
    userId,
    analytics,
    workflowId,
    storedBy: req.phlow.agent.agentId,
    timestamp: new Date().toISOString(),
  };
  
  mockDatabase.analytics.push(analyticsRecord);
  
  res.json({
    message: 'Analytics stored successfully',
    success: true,
    analyticsId: analyticsRecord.id,
    timestamp: new Date().toISOString(),
  });
});

// Error handling
app.use((error, req, res, next) => {
  console.error('Data agent error:', error);
  
  res.status(error.statusCode || 500).json({
    error: 'Data agent error',
    message: error.message,
    timestamp: new Date().toISOString(),
  });
});

app.listen(port, () => {
  console.log(`🗄️  Data Agent running on port ${port}`);
  console.log(`📋 Agent ID: ${dataAgentConfig.agentId}`);
  console.log(`🌐 Available at: http://localhost:${port}`);
});