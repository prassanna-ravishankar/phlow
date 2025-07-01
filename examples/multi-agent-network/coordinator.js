require('dotenv').config();
const express = require('express');
const axios = require('axios');
const { PhlowMiddleware, generateToken } = require('phlow-auth');

const app = express();
const port = process.env.COORDINATOR_PORT || 4000;

// Coordinator agent configuration
const coordinatorConfig = {
  agentId: 'coordinator-agent',
  name: 'Network Coordinator',
  description: 'Orchestrates multi-agent workflows',
  permissions: ['coordinate:workflows', 'read:data', 'write:data', 'compute:tasks'],
  publicKey: process.env.COORDINATOR_PUBLIC_KEY?.replace(/\\n/g, '\n'),
};

const phlow = new PhlowMiddleware({
  supabaseUrl: process.env.SUPABASE_URL,
  supabaseAnonKey: process.env.SUPABASE_ANON_KEY,
  agentCard: coordinatorConfig,
  privateKey: process.env.COORDINATOR_PRIVATE_KEY?.replace(/\\n/g, '\n'),
  options: {
    enableAudit: true,
    rateLimiting: {
      maxRequests: 200,
      windowMs: 60000,
    },
  },
});

app.use(express.json());

// Agent endpoints configuration
const agents = {
  data: {
    url: `http://localhost:${process.env.DATA_AGENT_PORT || 4001}`,
    id: 'data-agent',
  },
  auth: {
    url: `http://localhost:${process.env.AUTH_AGENT_PORT || 4002}`,
    id: 'auth-agent',
  },
  compute: {
    url: `http://localhost:${process.env.COMPUTE_AGENT_PORT || 4003}`,
    id: 'compute-agent',
  },
};

// Helper function to generate tokens for inter-agent communication
function generateAgentToken(targetAgentId, permissions = []) {
  return generateToken(
    coordinatorConfig,
    process.env.COORDINATOR_PRIVATE_KEY?.replace(/\\n/g, '\n'),
    targetAgentId,
    '10m'
  );
}

// Helper function to make authenticated requests to other agents
async function makeAgentRequest(agentType, endpoint, method = 'GET', data = null) {
  const agent = agents[agentType];
  if (!agent) {
    throw new Error(`Unknown agent type: ${agentType}`);
  }

  const token = generateAgentToken(agent.id);
  const config = {
    method,
    url: `${agent.url}${endpoint}`,
    headers: {
      'Authorization': `Bearer ${token}`,
      'X-Phlow-Agent-Id': coordinatorConfig.agentId,
      'Content-Type': 'application/json',
    },
  };

  if (data) {
    config.data = data;
  }

  try {
    const response = await axios(config);
    return response.data;
  } catch (error) {
    console.error(`Error communicating with ${agentType} agent:`, error.message);
    throw error;
  }
}

// Public endpoints
app.get('/', (req, res) => {
  res.json({
    message: 'Multi-Agent Network Coordinator',
    agent: coordinatorConfig,
    network: {
      agents: Object.entries(agents).map(([type, config]) => ({
        type,
        id: config.id,
        url: config.url,
      })),
    },
    workflows: [
      'GET /workflow/user-analysis',
      'POST /workflow/data-processing',
      'GET /workflow/system-status',
    ],
  });
});

app.get('/health', (req, res) => {
  res.json({
    status: 'healthy',
    timestamp: new Date().toISOString(),
    uptime: process.uptime(),
  });
});

// Network status endpoint
app.get('/network/status', async (req, res) => {
  const status = {};
  
  for (const [type, agent] of Object.entries(agents)) {
    try {
      const response = await makeAgentRequest(type, '/health');
      status[type] = {
        status: 'online',
        agent: agent.id,
        ...response,
      };
    } catch (error) {
      status[type] = {
        status: 'offline',
        agent: agent.id,
        error: error.message,
      };
    }
  }

  res.json({
    coordinator: 'online',
    agents: status,
    timestamp: new Date().toISOString(),
  });
});

// Complex workflow: User analysis
app.get('/workflow/user-analysis', phlow.authenticate(), async (req, res) => {
  const workflowId = `workflow-${Date.now()}`;
  
  try {
    console.log(`🔄 Starting user analysis workflow: ${workflowId}`);
    
    // Step 1: Validate user with auth agent
    const authResult = await makeAgentRequest('auth', '/validate-user', 'POST', {
      userId: req.query.userId || 'user-123',
      requestId: workflowId,
    });

    if (!authResult.valid) {
      return res.status(403).json({
        error: 'User validation failed',
        workflowId,
        details: authResult,
      });
    }

    // Step 2: Fetch user data
    const userData = await makeAgentRequest('data', '/users/profile', 'GET');
    
    // Step 3: Compute analytics
    const analytics = await makeAgentRequest('compute', '/analyze', 'POST', {
      data: userData,
      type: 'user-behavior',
      workflowId,
    });

    // Step 4: Store results
    const storageResult = await makeAgentRequest('data', '/analytics/store', 'POST', {
      userId: req.query.userId || 'user-123',
      analytics,
      workflowId,
    });

    console.log(`✅ Completed user analysis workflow: ${workflowId}`);

    res.json({
      message: 'User analysis completed successfully',
      workflowId,
      results: {
        user: authResult.user,
        analytics: analytics.results,
        stored: storageResult.success,
      },
      timestamp: new Date().toISOString(),
    });

  } catch (error) {
    console.error(`❌ Workflow ${workflowId} failed:`, error.message);
    
    res.status(500).json({
      error: 'Workflow failed',
      workflowId,
      message: error.message,
      timestamp: new Date().toISOString(),
    });
  }
});

// Data processing workflow
app.post('/workflow/data-processing', phlow.authenticate(), async (req, res) => {
  const workflowId = `processing-${Date.now()}`;
  const { dataset, operation } = req.body;

  try {
    console.log(`🔄 Starting data processing workflow: ${workflowId}`);

    // Step 1: Validate dataset access
    const dataValidation = await makeAgentRequest('data', '/datasets/validate', 'POST', {
      dataset,
      operation,
      requesterId: req.phlow.agent.agentId,
    });

    if (!dataValidation.authorized) {
      return res.status(403).json({
        error: 'Dataset access denied',
        workflowId,
        dataset,
      });
    }

    // Step 2: Fetch dataset
    const datasetContent = await makeAgentRequest('data', `/datasets/${dataset}`, 'GET');

    // Step 3: Process data
    const processingResult = await makeAgentRequest('compute', '/process', 'POST', {
      data: datasetContent,
      operation,
      workflowId,
    });

    // Step 4: Store processed results
    const storageResult = await makeAgentRequest('data', '/datasets/results', 'POST', {
      originalDataset: dataset,
      processedData: processingResult.output,
      operation,
      workflowId,
    });

    console.log(`✅ Completed data processing workflow: ${workflowId}`);

    res.json({
      message: 'Data processing completed successfully',
      workflowId,
      results: {
        operation,
        dataset,
        output: processingResult.output,
        stored: storageResult.success,
      },
      timestamp: new Date().toISOString(),
    });

  } catch (error) {
    console.error(`❌ Processing workflow ${workflowId} failed:`, error.message);
    
    res.status(500).json({
      error: 'Processing workflow failed',
      workflowId,
      message: error.message,
      timestamp: new Date().toISOString(),
    });
  }
});

// System status workflow
app.get('/workflow/system-status', phlow.authenticate(), async (req, res) => {
  try {
    // Gather status from all agents in parallel
    const statusPromises = Object.entries(agents).map(async ([type, agent]) => {
      try {
        const status = await makeAgentRequest(type, '/status', 'GET');
        return { type, status: 'healthy', details: status };
      } catch (error) {
        return { type, status: 'unhealthy', error: error.message };
      }
    });

    const agentStatuses = await Promise.all(statusPromises);

    // Aggregate system metrics
    const systemMetrics = {
      totalAgents: agentStatuses.length,
      healthyAgents: agentStatuses.filter(a => a.status === 'healthy').length,
      unhealthyAgents: agentStatuses.filter(a => a.status === 'unhealthy').length,
      uptime: process.uptime(),
      timestamp: new Date().toISOString(),
    };

    res.json({
      message: 'System status retrieved successfully',
      coordinator: {
        status: 'healthy',
        uptime: process.uptime(),
      },
      agents: agentStatuses,
      metrics: systemMetrics,
      health: systemMetrics.unhealthyAgents === 0 ? 'good' : 'degraded',
    });

  } catch (error) {
    res.status(500).json({
      error: 'Failed to retrieve system status',
      message: error.message,
      timestamp: new Date().toISOString(),
    });
  }
});

// Error handling
app.use((error, req, res, next) => {
  console.error('Coordinator error:', error);
  
  res.status(error.statusCode || 500).json({
    error: 'Coordinator error',
    message: error.message,
    timestamp: new Date().toISOString(),
  });
});

app.listen(port, () => {
  console.log(`🎯 Multi-Agent Network Coordinator running on port ${port}`);
  console.log(`📋 Agent ID: ${coordinatorConfig.agentId}`);
  console.log(`🌐 Available at: http://localhost:${port}`);
  console.log(`🔗 Network status: http://localhost:${port}/network/status`);
  console.log('\\n🤖 Connected agents:');
  Object.entries(agents).forEach(([type, agent]) => {
    console.log(`   ${type}: ${agent.url} (${agent.id})`);
  });
});