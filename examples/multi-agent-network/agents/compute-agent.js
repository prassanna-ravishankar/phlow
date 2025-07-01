require('dotenv').config();
const express = require('express');
const { PhlowMiddleware } = require('phlow-auth');

const app = express();
const port = process.env.COMPUTE_AGENT_PORT || 4003;

const computeAgentConfig = {
  agentId: 'compute-agent',
  name: 'Compute Processing Agent',
  description: 'Handles computational tasks and data analysis',
  permissions: ['compute:tasks', 'analyze:data', 'process:datasets'],
  publicKey: process.env.COMPUTE_AGENT_PUBLIC_KEY?.replace(/\\n/g, '\n'),
};

const phlow = new PhlowMiddleware({
  supabaseUrl: process.env.SUPABASE_URL,
  supabaseAnonKey: process.env.SUPABASE_ANON_KEY,
  agentCard: computeAgentConfig,
  privateKey: process.env.COMPUTE_AGENT_PRIVATE_KEY?.replace(/\\n/g, '\n'),
  options: {
    enableAudit: true,
  },
});

app.use(express.json());

// Mock computational results database
const mockComputeDatabase = {
  tasks: [],
  results: [],
  analytics: [],
};

// Computational helper functions
function analyzeUserBehavior(userData) {
  const { activity } = userData;
  
  // Mock analysis algorithms
  const engagementScore = Math.min(100, (activity.sessionCount * 2) + (activity.totalActions / 50));
  const activityLevel = activity.totalActions > 1000 ? 'high' : 
                       activity.totalActions > 500 ? 'medium' : 'low';
  
  const lastLoginDate = new Date(activity.lastLogin);
  const daysSinceLogin = Math.floor((Date.now() - lastLoginDate) / (1000 * 60 * 60 * 24));
  const recency = daysSinceLogin < 7 ? 'recent' : daysSinceLogin < 30 ? 'moderate' : 'stale';
  
  return {
    engagementScore: Math.round(engagementScore),
    activityLevel,
    recency,
    recommendations: generateRecommendations(engagementScore, activityLevel, recency),
    computedAt: new Date().toISOString(),
  };
}

function generateRecommendations(engagement, activity, recency) {
  const recommendations = [];
  
  if (engagement < 30) {
    recommendations.push('Increase user engagement through personalized content');
  }
  if (activity === 'low') {
    recommendations.push('Send activation campaign to boost user activity');
  }
  if (recency === 'stale') {
    recommendations.push('Re-engagement campaign needed');
  }
  if (engagement > 80 && activity === 'high') {
    recommendations.push('User is highly engaged - consider premium offerings');
  }
  
  return recommendations;
}

function processDataset(data, operation) {
  const records = data.records || [];
  
  switch (operation) {
    case 'sum':
      return {
        operation,
        result: records.reduce((sum, record) => sum + (record.amount || 0), 0),
        recordCount: records.length,
      };
      
    case 'average':
      const total = records.reduce((sum, record) => sum + (record.amount || 0), 0);
      return {
        operation,
        result: records.length > 0 ? total / records.length : 0,
        recordCount: records.length,
      };
      
    case 'group_by_region':
      const grouped = records.reduce((acc, record) => {
        const region = record.region || 'unknown';
        if (!acc[region]) acc[region] = [];
        acc[region].push(record);
        return acc;
      }, {});
      
      return {
        operation,
        result: Object.entries(grouped).map(([region, regionRecords]) => ({
          region,
          count: regionRecords.length,
          totalAmount: regionRecords.reduce((sum, r) => sum + (r.amount || 0), 0),
        })),
        recordCount: records.length,
      };
      
    default:
      return {
        operation,
        result: `Processed ${records.length} records with operation: ${operation}`,
        recordCount: records.length,
      };
  }
}

// Public endpoints
app.get('/', (req, res) => {
  res.json({
    message: 'Compute Processing Agent',
    agent: computeAgentConfig,
    capabilities: [
      'User behavior analysis',
      'Dataset processing',
      'Statistical computations',
      'Machine learning inference',
    ],
    availableOperations: [
      'analyze (user-behavior)',
      'process (sum, average, group_by_region)',
    ],
  });
});

app.get('/health', (req, res) => {
  res.json({
    status: 'healthy',
    timestamp: new Date().toISOString(),
    uptime: process.uptime(),
    compute: {
      tasksCompleted: mockComputeDatabase.tasks.length,
      resultsStored: mockComputeDatabase.results.length,
      analyticsGenerated: mockComputeDatabase.analytics.length,
    },
  });
});

app.get('/status', phlow.authenticate(), (req, res) => {
  const recentTasks = mockComputeDatabase.tasks.slice(-5);
  
  res.json({
    agent: computeAgentConfig.name,
    status: 'operational',
    computing: {
      totalTasks: mockComputeDatabase.tasks.length,
      completedTasks: mockComputeDatabase.tasks.filter(t => t.status === 'completed').length,
      failedTasks: mockComputeDatabase.tasks.filter(t => t.status === 'failed').length,
      recentTasks: recentTasks.map(t => ({
        id: t.id,
        type: t.type,
        status: t.status,
        completedAt: t.completedAt,
      })),
    },
    requestedBy: req.phlow.agent.agentId,
    timestamp: new Date().toISOString(),
  });
});

// Analysis endpoint
app.post('/analyze', phlow.authenticate({ requiredPermissions: ['compute:tasks'] }), (req, res) => {
  const { data, type, workflowId } = req.body;
  
  if (!data || !type) {
    return res.status(400).json({
      error: 'Data and analysis type are required',
    });
  }

  const taskId = `task-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
  
  try {
    let results;
    
    switch (type) {
      case 'user-behavior':
        results = analyzeUserBehavior(data.user);
        break;
        
      default:
        return res.status(400).json({
          error: 'Unsupported analysis type',
          supportedTypes: ['user-behavior'],
        });
    }

    const task = {
      id: taskId,
      type,
      workflowId,
      status: 'completed',
      requestedBy: req.phlow.agent.agentId,
      startedAt: new Date().toISOString(),
      completedAt: new Date().toISOString(),
      data: {
        inputSize: JSON.stringify(data).length,
        outputSize: JSON.stringify(results).length,
      },
    };

    mockComputeDatabase.tasks.push(task);
    mockComputeDatabase.analytics.push({
      taskId,
      type,
      results,
      workflowId,
      timestamp: new Date().toISOString(),
    });

    console.log(`🧠 Completed analysis task: ${taskId} (${type})`);

    res.json({
      message: 'Analysis completed successfully',
      taskId,
      type,
      results,
      workflowId,
      processedBy: req.phlow.agent.agentId,
      timestamp: new Date().toISOString(),
    });

  } catch (error) {
    const task = {
      id: taskId,
      type,
      workflowId,
      status: 'failed',
      requestedBy: req.phlow.agent.agentId,
      startedAt: new Date().toISOString(),
      failedAt: new Date().toISOString(),
      error: error.message,
    };

    mockComputeDatabase.tasks.push(task);

    console.error(`❌ Analysis task failed: ${taskId}`, error);

    res.status(500).json({
      error: 'Analysis failed',
      taskId,
      message: error.message,
      timestamp: new Date().toISOString(),
    });
  }
});

// Data processing endpoint
app.post('/process', phlow.authenticate({ requiredPermissions: ['process:datasets'] }), (req, res) => {
  const { data, operation, workflowId } = req.body;
  
  if (!data || !operation) {
    return res.status(400).json({
      error: 'Data and operation are required',
    });
  }

  const taskId = `process-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
  
  try {
    const output = processDataset(data.dataset, operation);
    
    const task = {
      id: taskId,
      type: 'data-processing',
      operation,
      workflowId,
      status: 'completed',
      requestedBy: req.phlow.agent.agentId,
      startedAt: new Date().toISOString(),
      completedAt: new Date().toISOString(),
      data: {
        inputRecords: data.dataset?.records?.length || 0,
        operation,
      },
    };

    mockComputeDatabase.tasks.push(task);
    mockComputeDatabase.results.push({
      taskId,
      operation,
      output,
      workflowId,
      timestamp: new Date().toISOString(),
    });

    console.log(`🔢 Completed processing task: ${taskId} (${operation})`);

    res.json({
      message: 'Data processing completed successfully',
      taskId,
      operation,
      output,
      workflowId,
      processedBy: req.phlow.agent.agentId,
      timestamp: new Date().toISOString(),
    });

  } catch (error) {
    const task = {
      id: taskId,
      type: 'data-processing',
      operation,
      workflowId,
      status: 'failed',
      requestedBy: req.phlow.agent.agentId,
      startedAt: new Date().toISOString(),
      failedAt: new Date().toISOString(),
      error: error.message,
    };

    mockComputeDatabase.tasks.push(task);

    console.error(`❌ Processing task failed: ${taskId}`, error);

    res.status(500).json({
      error: 'Data processing failed',
      taskId,
      message: error.message,
      timestamp: new Date().toISOString(),
    });
  }
});

// Task status endpoint
app.get('/tasks/:taskId', phlow.authenticate(), (req, res) => {
  const { taskId } = req.params;
  const task = mockComputeDatabase.tasks.find(t => t.id === taskId);
  
  if (!task) {
    return res.status(404).json({
      error: 'Task not found',
      taskId,
    });
  }

  res.json({
    message: 'Task details retrieved',
    task,
    requestedBy: req.phlow.agent.agentId,
    timestamp: new Date().toISOString(),
  });
});

// Error handling
app.use((error, req, res, next) => {
  console.error('Compute agent error:', error);
  
  res.status(error.statusCode || 500).json({
    error: 'Compute agent error',
    message: error.message,
    timestamp: new Date().toISOString(),
  });
});

app.listen(port, () => {
  console.log(`🧠 Compute Agent running on port ${port}`);
  console.log(`📋 Agent ID: ${computeAgentConfig.agentId}`);
  console.log(`🌐 Available at: http://localhost:${port}`);
});