require('dotenv').config();
const express = require('express');
const { PhlowMiddleware } = require('phlow-auth');

const app = express();
const port = process.env.AUTH_AGENT_PORT || 4002;

const authAgentConfig = {
  agentId: 'auth-agent',
  name: 'Authentication Agent',
  description: 'Handles user authentication and authorization',
  permissions: ['auth:validate', 'auth:manage', 'read:users'],
  publicKey: process.env.AUTH_AGENT_PUBLIC_KEY?.replace(/\\n/g, '\n'),
};

const phlow = new PhlowMiddleware({
  supabaseUrl: process.env.SUPABASE_URL,
  supabaseAnonKey: process.env.SUPABASE_ANON_KEY,
  agentCard: authAgentConfig,
  privateKey: process.env.AUTH_AGENT_PRIVATE_KEY?.replace(/\\n/g, '\n'),
  options: {
    enableAudit: true,
  },
});

app.use(express.json());

// Mock authentication database
const mockAuthDatabase = {
  users: {
    'user-123': {
      id: 'user-123',
      username: 'alice_johnson',
      email: 'alice@example.com',
      status: 'active',
      roles: ['user', 'premium'],
      permissions: ['read:own_data', 'write:own_data'],
      lastLogin: '2024-01-15T10:30:00Z',
      failedAttempts: 0,
      isLocked: false,
    },
    'user-456': {
      id: 'user-456',
      username: 'bob_smith',
      email: 'bob@example.com',
      status: 'active',
      roles: ['admin'],
      permissions: ['read:all_data', 'write:all_data', 'admin:users'],
      lastLogin: '2024-01-14T15:20:00Z',
      failedAttempts: 0,
      isLocked: false,
    },
  },
  sessions: {},
  auditLog: [],
};

// Helper function to log auth events
function logAuthEvent(event, userId, details = {}) {
  const logEntry = {
    timestamp: new Date().toISOString(),
    event,
    userId,
    details,
    id: `audit-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
  };
  
  mockAuthDatabase.auditLog.push(logEntry);
  console.log(`🔐 Auth Event: ${event} for user ${userId}`);
}

// Public endpoints
app.get('/', (req, res) => {
  res.json({
    message: 'Authentication Agent',
    agent: authAgentConfig,
    capabilities: [
      'User validation',
      'Permission checking',
      'Session management',
      'Authentication audit',
    ],
  });
});

app.get('/health', (req, res) => {
  res.json({
    status: 'healthy',
    timestamp: new Date().toISOString(),
    uptime: process.uptime(),
    database: {
      users: Object.keys(mockAuthDatabase.users).length,
      activeSessions: Object.keys(mockAuthDatabase.sessions).length,
      auditEntries: mockAuthDatabase.auditLog.length,
    },
  });
});

app.get('/status', phlow.authenticate(), (req, res) => {
  res.json({
    agent: authAgentConfig.name,
    status: 'operational',
    authentication: {
      totalUsers: Object.keys(mockAuthDatabase.users).length,
      activeUsers: Object.values(mockAuthDatabase.users).filter(u => u.status === 'active').length,
      lockedUsers: Object.values(mockAuthDatabase.users).filter(u => u.isLocked).length,
      activeSessions: Object.keys(mockAuthDatabase.sessions).length,
      recentAuditEntries: mockAuthDatabase.auditLog.slice(-5),
    },
    requestedBy: req.phlow.agent.agentId,
    timestamp: new Date().toISOString(),
  });
});

// User validation endpoint
app.post('/validate-user', phlow.authenticate({ requiredPermissions: ['auth:validate'] }), (req, res) => {
  const { userId, requestId } = req.body;
  
  if (!userId) {
    return res.status(400).json({
      error: 'User ID required',
      valid: false,
    });
  }

  const user = mockAuthDatabase.users[userId];
  
  if (!user) {
    logAuthEvent('validation_failed', userId, { 
      reason: 'user_not_found',
      requestId,
      requestedBy: req.phlow.agent.agentId,
    });
    
    return res.json({
      valid: false,
      reason: 'User not found',
      userId,
      requestId,
    });
  }

  if (user.isLocked) {
    logAuthEvent('validation_failed', userId, { 
      reason: 'account_locked',
      requestId,
      requestedBy: req.phlow.agent.agentId,
    });
    
    return res.json({
      valid: false,
      reason: 'Account locked',
      userId,
      requestId,
    });
  }

  if (user.status !== 'active') {
    logAuthEvent('validation_failed', userId, { 
      reason: 'account_inactive',
      status: user.status,
      requestId,
      requestedBy: req.phlow.agent.agentId,
    });
    
    return res.json({
      valid: false,
      reason: 'Account inactive',
      status: user.status,
      userId,
      requestId,
    });
  }

  logAuthEvent('validation_success', userId, { 
    requestId,
    requestedBy: req.phlow.agent.agentId,
  });

  res.json({
    valid: true,
    user: {
      id: user.id,
      username: user.username,
      email: user.email,
      roles: user.roles,
      permissions: user.permissions,
      lastLogin: user.lastLogin,
    },
    requestId,
    timestamp: new Date().toISOString(),
  });
});

// Permission checking endpoint
app.post('/check-permissions', phlow.authenticate({ requiredPermissions: ['auth:validate'] }), (req, res) => {
  const { userId, requiredPermissions } = req.body;
  
  if (!userId || !requiredPermissions) {
    return res.status(400).json({
      error: 'User ID and required permissions are required',
    });
  }

  const user = mockAuthDatabase.users[userId];
  
  if (!user) {
    return res.status(404).json({
      error: 'User not found',
      userId,
    });
  }

  const hasPermissions = requiredPermissions.every(permission => 
    user.permissions.includes(permission)
  );

  logAuthEvent('permission_check', userId, {
    requiredPermissions,
    userPermissions: user.permissions,
    granted: hasPermissions,
    requestedBy: req.phlow.agent.agentId,
  });

  res.json({
    userId,
    requiredPermissions,
    userPermissions: user.permissions,
    hasPermissions,
    timestamp: new Date().toISOString(),
  });
});

// Session management
app.post('/sessions/create', phlow.authenticate({ requiredPermissions: ['auth:manage'] }), (req, res) => {
  const { userId } = req.body;
  
  const user = mockAuthDatabase.users[userId];
  if (!user) {
    return res.status(404).json({
      error: 'User not found',
      userId,
    });
  }

  const sessionId = `session-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
  const session = {
    id: sessionId,
    userId,
    createdAt: new Date().toISOString(),
    lastActivity: new Date().toISOString(),
    createdBy: req.phlow.agent.agentId,
  };

  mockAuthDatabase.sessions[sessionId] = session;

  logAuthEvent('session_created', userId, {
    sessionId,
    createdBy: req.phlow.agent.agentId,
  });

  res.json({
    message: 'Session created successfully',
    session,
    timestamp: new Date().toISOString(),
  });
});

app.delete('/sessions/:sessionId', phlow.authenticate({ requiredPermissions: ['auth:manage'] }), (req, res) => {
  const { sessionId } = req.params;
  const session = mockAuthDatabase.sessions[sessionId];
  
  if (!session) {
    return res.status(404).json({
      error: 'Session not found',
      sessionId,
    });
  }

  delete mockAuthDatabase.sessions[sessionId];

  logAuthEvent('session_terminated', session.userId, {
    sessionId,
    terminatedBy: req.phlow.agent.agentId,
  });

  res.json({
    message: 'Session terminated successfully',
    sessionId,
    timestamp: new Date().toISOString(),
  });
});

// Audit endpoints
app.get('/audit/logs', phlow.authenticate({ requiredPermissions: ['auth:manage'] }), (req, res) => {
  const limit = parseInt(req.query.limit) || 50;
  const offset = parseInt(req.query.offset) || 0;
  
  const logs = mockAuthDatabase.auditLog
    .slice(-limit - offset, -offset || undefined)
    .reverse();

  res.json({
    message: 'Audit logs retrieved',
    logs,
    total: mockAuthDatabase.auditLog.length,
    limit,
    offset,
    requestedBy: req.phlow.agent.agentId,
    timestamp: new Date().toISOString(),
  });
});

// Error handling
app.use((error, req, res, next) => {
  console.error('Auth agent error:', error);
  
  res.status(error.statusCode || 500).json({
    error: 'Auth agent error',
    message: error.message,
    timestamp: new Date().toISOString(),
  });
});

app.listen(port, () => {
  console.log(`🔐 Auth Agent running on port ${port}`);
  console.log(`📋 Agent ID: ${authAgentConfig.agentId}`);
  console.log(`🌐 Available at: http://localhost:${port}`);
});