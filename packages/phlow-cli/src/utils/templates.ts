import fs from 'fs-extra';
import path from 'path';

export const BASIC_AGENT_TEMPLATE = `const express = require('express');
const { PhlowMiddleware } = require('phlow-auth');

const app = express();
const port = process.env.PORT || 3000;

// Initialize Phlow middleware
const phlow = new PhlowMiddleware({
  supabaseUrl: process.env.SUPABASE_URL,
  supabaseAnonKey: process.env.SUPABASE_ANON_KEY,
  agentCard: {
    agentId: '{{AGENT_ID}}',
    name: '{{AGENT_NAME}}',
    description: '{{AGENT_DESCRIPTION}}',
    permissions: {{AGENT_PERMISSIONS}},
    publicKey: process.env.AGENT_PUBLIC_KEY,
  },
  privateKey: process.env.AGENT_PRIVATE_KEY,
});

app.use(express.json());

// Protected route
app.get('/protected', phlow.authenticate(), (req, res) => {
  res.json({
    message: 'Hello from protected endpoint!',
    agent: req.phlow.agent.name,
    permissions: req.phlow.claims.permissions,
  });
});

// Health check
app.get('/health', (req, res) => {
  res.json({ status: 'ok', timestamp: new Date().toISOString() });
});

app.listen(port, () => {
  console.log(\`Agent listening on port \${port}\`);
});
`;

export const ENV_TEMPLATE = `# Supabase Configuration
SUPABASE_URL={{SUPABASE_URL}}
SUPABASE_ANON_KEY={{SUPABASE_ANON_KEY}}

# Agent Keys
AGENT_PUBLIC_KEY="{{AGENT_PUBLIC_KEY}}"
AGENT_PRIVATE_KEY="{{AGENT_PRIVATE_KEY}}"

# Server Configuration  
PORT=3000
`;

export const PACKAGE_JSON_TEMPLATE = `{
  "name": "{{PACKAGE_NAME}}",
  "version": "1.0.0",
  "description": "Basic Phlow agent",
  "main": "index.js",
  "scripts": {
    "start": "node index.js",
    "dev": "nodemon index.js"
  },
  "dependencies": {
    "express": "^4.19.2",
    "phlow-auth": "^0.1.0",
    "dotenv": "^16.4.5"
  },
  "devDependencies": {
    "nodemon": "^3.1.0"
  }
}
`;

export const DOCKER_TEMPLATE = `FROM node:18-alpine

WORKDIR /app

COPY package*.json ./
RUN npm install --production

COPY . .

EXPOSE 3000

CMD ["npm", "start"]
`;

export const SUPABASE_SCHEMA = `-- Agent Cards table
CREATE TABLE agent_cards (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  agent_id TEXT UNIQUE NOT NULL,
  name TEXT NOT NULL,
  description TEXT,
  permissions TEXT[] DEFAULT '{}',
  public_key TEXT NOT NULL,
  endpoints JSONB DEFAULT '{}',
  metadata JSONB DEFAULT '{}',
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Audit logs table
CREATE TABLE phlow_audit_logs (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
  event TEXT NOT NULL,
  agent_id TEXT NOT NULL,
  target_agent_id TEXT,
  details JSONB DEFAULT '{}',
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Enable RLS
ALTER TABLE agent_cards ENABLE ROW LEVEL SECURITY;
ALTER TABLE phlow_audit_logs ENABLE ROW LEVEL SECURITY;

-- Basic RLS policies
CREATE POLICY agent_cards_read ON agent_cards
FOR SELECT
USING (true);

CREATE POLICY agent_cards_own ON agent_cards
FOR ALL
USING (agent_id = auth.jwt() ->> 'sub');

CREATE POLICY audit_logs_own ON phlow_audit_logs
FOR ALL
USING (
  agent_id = auth.jwt() ->> 'sub' 
  OR target_agent_id = auth.jwt() ->> 'sub'
);
`;

export async function writeTemplate(
  templatePath: string,
  content: string,
  replacements: Record<string, string> = {}
): Promise<void> {
  let processedContent = content;
  
  for (const [key, value] of Object.entries(replacements)) {
    const pattern = new RegExp(`{{${key}}}`, 'g');
    processedContent = processedContent.replace(pattern, value);
  }
  
  await fs.ensureDir(path.dirname(templatePath));
  await fs.writeFile(templatePath, processedContent);
}