-- Phlow Database Schema (A2A-compatible)
-- This schema supports both current Phlow usage and A2A Protocol compatibility

-- Drop existing tables if they exist
DROP TABLE IF EXISTS phlow_audit_logs;
DROP TABLE IF EXISTS agent_cards;

-- A2A-compatible Agent Cards table
CREATE TABLE agent_cards (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  agent_id TEXT UNIQUE NOT NULL,
  name TEXT NOT NULL,
  description TEXT,
  public_key TEXT NOT NULL,
  
  -- A2A Protocol fields
  schema_version TEXT DEFAULT '0.1.0',
  service_url TEXT,
  skills JSONB DEFAULT '[]',
  security_schemes JSONB DEFAULT '{"phlow-jwt": {"type": "http", "scheme": "bearer", "bearerFormat": "JWT"}}',
  
  -- Metadata and timestamps
  metadata JSONB DEFAULT '{}',
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Simplified audit logs table
CREATE TABLE phlow_audit_logs (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
  event TEXT NOT NULL,
  agent_id TEXT NOT NULL,
  target_agent_id TEXT,
  details JSONB DEFAULT '{}',
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes for performance
CREATE INDEX idx_agent_cards_agent_id ON agent_cards(agent_id);
CREATE INDEX idx_audit_logs_agent_id ON phlow_audit_logs(agent_id);
CREATE INDEX idx_audit_logs_timestamp ON phlow_audit_logs(timestamp);

-- Enable Row Level Security
ALTER TABLE agent_cards ENABLE ROW LEVEL SECURITY;
ALTER TABLE phlow_audit_logs ENABLE ROW LEVEL SECURITY;

-- Basic RLS policies
-- Allow all agents to read agent cards (for public key lookup)
CREATE POLICY agent_cards_read ON agent_cards 
  FOR SELECT USING (true);

-- Allow agents to update their own card
CREATE POLICY agent_cards_own ON agent_cards 
  FOR ALL USING (agent_id = current_setting('phlow.agent_id', true));

-- Allow agents to read their own audit logs
CREATE POLICY audit_logs_own ON phlow_audit_logs 
  FOR SELECT USING (
    agent_id = current_setting('phlow.agent_id', true) OR 
    target_agent_id = current_setting('phlow.agent_id', true)
  );

-- Function to update the updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ language 'plpgsql';

-- Trigger to auto-update the updated_at column
CREATE TRIGGER update_agent_cards_updated_at 
  BEFORE UPDATE ON agent_cards 
  FOR EACH ROW 
  EXECUTE FUNCTION update_updated_at_column();

-- Sample data for testing
INSERT INTO agent_cards (agent_id, name, description, public_key, service_url, skills) VALUES
(
  'example-agent',
  'Example Agent',
  'A sample agent for testing',
  '-----BEGIN PUBLIC KEY-----
MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEA1234567890...
-----END PUBLIC KEY-----',
  'https://example-agent.com',
  '[{"name": "data-processing", "description": "Process and analyze data"}]'::jsonb
);