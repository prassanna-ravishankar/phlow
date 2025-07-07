/**
 * Minimal example showing Phlow as an A2A SDK extension with Supabase
 */

import express from 'express';
import { PhlowMiddleware } from 'phlow-auth';

// Standard A2A Protocol agent card
const agentCard = {
  schemaVersion: '1.0',
  name: 'Analytics Agent',
  description: 'Provides data analysis services',
  serviceUrl: 'https://analytics-agent.example.com',
  skills: [
    { name: 'data-analysis', description: 'Analyze datasets' },
    { name: 'visualization', description: 'Create charts and graphs' }
  ],
  securitySchemes: {
    'bearer-jwt': {
      type: 'http',
      scheme: 'bearer',
      bearerFormat: 'JWT'
    }
  },
  metadata: {
    agentId: 'analytics-agent-001',
    publicKey: process.env.PUBLIC_KEY
  }
};

// Initialize Phlow (extends A2A SDK)
const phlow = new PhlowMiddleware({
  // A2A Protocol configuration
  agentCard,
  privateKey: process.env.PRIVATE_KEY,
  
  // Phlow's Supabase enhancements
  supabaseUrl: process.env.SUPABASE_URL,
  supabaseAnonKey: process.env.SUPABASE_ANON_KEY,
  enableAuditLog: true,
  enableRateLimiting: true,
  rateLimitConfig: {
    windowMs: 60000,  // 1 minute
    maxRequests: 100
  }
});

const app = express();
app.use(express.json());

// A2A Protocol standard: well-known endpoint
// (Handled by A2A SDK, no custom code needed)
app.get('/.well-known/agent.json', phlow.wellKnownHandler());

// Protected endpoint using A2A authentication + Supabase features
app.post('/api/analyze', phlow.authenticate(), async (req, res) => {
  // A2A context is available
  const { agent, supabase } = req.phlow;
  
  console.log(`Request from agent: ${agent.name}`);
  
  // Use Supabase for data operations with automatic RLS
  const { data, error } = await supabase
    .from('analysis_jobs')
    .insert({
      agent_id: agent.metadata.agentId,
      dataset: req.body.dataset,
      status: 'processing'
    })
    .select()
    .single();
  
  if (error) {
    return res.status(500).json({ error: 'Failed to create job' });
  }
  
  res.json({
    jobId: data.id,
    message: 'Analysis job created',
    estimatedTime: '5 minutes'
  });
});

// Generate RLS policy for the table
const rlsPolicy = phlow.generateRLSPolicy('analytics-agent-001', ['read', 'write']);
console.log('Apply this RLS policy to your Supabase table:');
console.log(rlsPolicy);

// Register this agent in Supabase registry
await phlow.registerAgent(agentCard);

app.listen(3000, () => {
  console.log('A2A-compliant agent with Supabase running on port 3000');
});