const express = require('express');
const { PhlowMiddleware } = require('phlow-auth-js');
require('dotenv').config();

const app = express();
app.use(express.json());

// Initialize Phlow with A2A-compatible AgentCard
const phlow = new PhlowMiddleware({
  supabaseUrl: process.env.SUPABASE_URL,
  supabaseAnonKey: process.env.SUPABASE_ANON_KEY,
  agentCard: {
    agentId: 'a2a-example-agent',
    name: 'A2A Example Agent',
    description: 'An example agent demonstrating A2A Protocol compatibility',
    publicKey: process.env.PUBLIC_KEY,
    serviceUrl: process.env.SERVICE_URL || 'http://localhost:3000',
    schemaVersion: '0.1.0',
    skills: [
      {
        name: 'echo',
        description: 'Echo back messages'
      },
      {
        name: 'process-data',
        description: 'Process and transform data'
      }
    ],
    securitySchemes: {
      'phlow-jwt': {
        type: 'http',
        scheme: 'bearer',
        bearerFormat: 'JWT',
        description: 'Phlow JWT authentication'
      }
    }
  },
  privateKey: process.env.PRIVATE_KEY
});

// A2A Protocol: Well-known endpoint for agent discovery
app.get('/.well-known/agent.json', phlow.wellKnownHandler());

// A2A Protocol: Main service endpoint (future JSON-RPC support)
app.post('/a2a', phlow.authenticate(), (req, res) => {
  // This will eventually handle JSON-RPC requests
  // For now, it's a placeholder showing authentication works
  res.json({
    message: 'A2A endpoint ready',
    agent: req.phlow.agent.name,
    skills: req.phlow.claims.skills
  });
});

// Traditional REST endpoints (current implementation)
app.get('/health', (req, res) => {
  res.json({
    status: 'healthy',
    agent: 'a2a-example-agent',
    timestamp: new Date().toISOString()
  });
});

// Protected endpoint requiring authentication
app.post('/echo', phlow.authenticate(), (req, res) => {
  const { agent, claims } = req.phlow;
  
  res.json({
    echo: req.body,
    processedBy: 'a2a-example-agent',
    requestFrom: agent.name,
    skills: claims.skills,
    timestamp: new Date().toISOString()
  });
});

// Process data endpoint
app.post('/process', phlow.authenticate(), (req, res) => {
  const { data, operation } = req.body;
  
  // Simple data processing based on operation
  let result;
  switch (operation) {
    case 'uppercase':
      result = data.toUpperCase();
      break;
    case 'reverse':
      result = data.split('').reverse().join('');
      break;
    case 'wordcount':
      result = data.split(/\s+/).length;
      break;
    default:
      result = data;
  }
  
  res.json({
    original: data,
    processed: result,
    operation,
    agent: 'a2a-example-agent'
  });
});

// Error handling
app.use((err, req, res, next) => {
  if (err.name === 'AuthenticationError') {
    return res.status(401).json({
      error: err.message,
      code: err.code
    });
  }
  
  res.status(500).json({
    error: 'Internal server error',
    message: err.message
  });
});

const PORT = process.env.PORT || 3000;
app.listen(PORT, () => {
  console.log(`A2A-compatible agent running on port ${PORT}`);
  console.log(`AgentCard available at: http://localhost:${PORT}/.well-known/agent.json`);
});