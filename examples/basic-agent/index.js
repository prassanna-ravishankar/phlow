require('dotenv').config();
const express = require('express');
const { PhlowMiddleware } = require('phlow-auth');

const app = express();
const port = process.env.PORT || 3000;

// Validate environment variables
const requiredEnvVars = [
  'SUPABASE_URL',
  'SUPABASE_ANON_KEY',
  'AGENT_ID',
  'AGENT_NAME',
  'AGENT_PUBLIC_KEY',
  'AGENT_PRIVATE_KEY'
];

for (const envVar of requiredEnvVars) {
  if (!process.env[envVar]) {
    console.error(`❌ Missing required environment variable: ${envVar}`);
    process.exit(1);
  }
}

// Parse agent permissions from environment
const permissions = process.env.AGENT_PERMISSIONS 
  ? process.env.AGENT_PERMISSIONS.split(',').map(p => p.trim())
  : ['read:data'];

// Initialize Phlow middleware
const phlow = new PhlowMiddleware({
  supabaseUrl: process.env.SUPABASE_URL,
  supabaseAnonKey: process.env.SUPABASE_ANON_KEY,
  agentCard: {
    agentId: process.env.AGENT_ID,
    name: process.env.AGENT_NAME,
    description: process.env.AGENT_DESCRIPTION || 'Basic Phlow agent example',
    permissions: permissions,
    publicKey: process.env.AGENT_PUBLIC_KEY.replace(/\\n/g, '\n'),
  },
  privateKey: process.env.AGENT_PRIVATE_KEY.replace(/\\n/g, '\n'),
  options: {
    enableAudit: true,
    rateLimiting: {
      maxRequests: 100,
      windowMs: 60000, // 1 minute
    },
  },
});

app.use(express.json());

// Middleware to log all requests
app.use((req, res, next) => {
  console.log(`${new Date().toISOString()} ${req.method} ${req.path}`);
  next();
});

// Public routes
app.get('/', (req, res) => {
  res.json({
    message: 'Basic Phlow Agent',
    agent: {
      id: process.env.AGENT_ID,
      name: process.env.AGENT_NAME,
      description: process.env.AGENT_DESCRIPTION || 'Basic Phlow agent example',
      permissions: permissions,
    },
    endpoints: {
      health: '/health',
      protected: '/protected',
      data: '/data',
      admin: '/admin',
    },
    documentation: 'https://github.com/phlowai/phlow',
  });
});

app.get('/health', (req, res) => {
  res.json({ 
    status: 'healthy', 
    timestamp: new Date().toISOString(),
    uptime: process.uptime(),
  });
});

// Protected routes with different permission requirements
app.get('/protected', phlow.authenticate(), (req, res) => {
  res.json({
    message: 'Hello from protected endpoint!',
    requestingAgent: {
      id: req.phlow.agent.agentId,
      name: req.phlow.agent.name,
      permissions: req.phlow.claims.permissions,
    },
    timestamp: new Date().toISOString(),
  });
});

app.get('/data', phlow.authenticate({ requiredPermissions: ['read:data'] }), (req, res) => {
  res.json({
    message: 'Data access granted',
    data: {
      example: 'This is protected data',
      timestamp: new Date().toISOString(),
      accessedBy: req.phlow.agent.agentId,
    },
  });
});

app.post('/data', phlow.authenticate({ requiredPermissions: ['write:data'] }), (req, res) => {
  res.json({
    message: 'Data write access granted',
    received: req.body,
    processedBy: req.phlow.agent.agentId,
    timestamp: new Date().toISOString(),
  });
});

app.get('/admin', phlow.authenticate({ requiredPermissions: ['admin:users'] }), (req, res) => {
  res.json({
    message: 'Admin access granted',
    adminData: {
      totalUsers: 42,
      activeAgents: 7,
      systemStatus: 'operational',
    },
    accessedBy: req.phlow.agent.agentId,
    timestamp: new Date().toISOString(),
  });
});

// Token refresh middleware on all routes
app.use(phlow.refreshTokenIfNeeded());

// Error handling middleware
app.use((error, req, res, next) => {
  console.error('Error:', error);
  
  if (error.name === 'AuthenticationError') {
    return res.status(401).json({
      error: 'Authentication failed',
      code: error.code,
      message: error.message,
    });
  }
  
  if (error.name === 'AuthorizationError') {
    return res.status(403).json({
      error: 'Authorization failed',
      code: error.code,
      message: error.message,
    });
  }
  
  if (error.name === 'RateLimitError') {
    return res.status(429).json({
      error: 'Rate limit exceeded',
      code: error.code,
      message: error.message,
    });
  }
  
  res.status(500).json({
    error: 'Internal server error',
    message: error.message,
  });
});

app.listen(port, () => {
  console.log(`🚀 Basic Phlow Agent running on port ${port}`);
  console.log(`📋 Agent ID: ${process.env.AGENT_ID}`);
  console.log(`🔐 Permissions: ${permissions.join(', ')}`);
  console.log(`🌐 Available at: http://localhost:${port}`);
  console.log(`📖 Documentation: http://localhost:${port}/`);
});