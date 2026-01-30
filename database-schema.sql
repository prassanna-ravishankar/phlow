-- Phlow Database Schema (A2A-compatible)
-- This schema supports both current Phlow usage and A2A Protocol compatibility

-- Drop existing tables if they exist
DROP TABLE IF EXISTS verified_roles;
DROP TABLE IF EXISTS auth_audit_log;
DROP TABLE IF EXISTS did_public_keys;
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

-- Authentication audit logs table
CREATE TABLE auth_audit_log (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  agent_id TEXT NOT NULL,
  timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
  event_type TEXT NOT NULL,
  success BOOLEAN NOT NULL,
  metadata JSONB DEFAULT '{}',
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- DID public keys table for cryptographic verification
CREATE TABLE did_public_keys (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  did TEXT NOT NULL,
  key_fragment TEXT NOT NULL,
  public_key TEXT NOT NULL, -- Base64 encoded public key
  key_type TEXT NOT NULL, -- e.g., 'Ed25519', 'RSA'
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

  -- Ensure unique combination of DID and key fragment
  UNIQUE(did, key_fragment)
);

-- RBAC: Verified roles table for caching role credential verifications
CREATE TABLE verified_roles (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  agent_id TEXT NOT NULL,
  role TEXT NOT NULL,
  verified_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
  expires_at TIMESTAMP WITH TIME ZONE,
  credential_hash TEXT NOT NULL,
  issuer_did TEXT,
  metadata JSONB DEFAULT '{}',
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

  -- Ensure unique combination of agent and role
  UNIQUE(agent_id, role)
);

-- Indexes for performance
CREATE INDEX idx_agent_cards_agent_id ON agent_cards(agent_id);
CREATE INDEX idx_auth_audit_log_agent_id ON auth_audit_log(agent_id);
CREATE INDEX idx_auth_audit_log_timestamp ON auth_audit_log(timestamp);
CREATE INDEX idx_did_public_keys_did_fragment ON did_public_keys(did, key_fragment);
CREATE INDEX idx_did_public_keys_did ON did_public_keys(did);
CREATE INDEX idx_verified_roles_agent_role ON verified_roles(agent_id, role);
CREATE INDEX idx_verified_roles_expires ON verified_roles(expires_at);
CREATE INDEX idx_verified_roles_agent_id ON verified_roles(agent_id);

-- Enable Row Level Security
ALTER TABLE agent_cards ENABLE ROW LEVEL SECURITY;
ALTER TABLE auth_audit_log ENABLE ROW LEVEL SECURITY;
ALTER TABLE did_public_keys ENABLE ROW LEVEL SECURITY;
ALTER TABLE verified_roles ENABLE ROW LEVEL SECURITY;

-- Basic RLS policies
-- Allow all agents to read agent cards (for public key lookup)
CREATE POLICY agent_cards_read ON agent_cards
  FOR SELECT USING (true);

-- Allow agents to update their own card
CREATE POLICY agent_cards_own ON agent_cards
  FOR ALL USING (agent_id = current_setting('phlow.agent_id', true));

-- Allow agents to read their own audit logs
CREATE POLICY auth_audit_log_own ON auth_audit_log
  FOR SELECT USING (
    agent_id = current_setting('phlow.agent_id', true)
  );

-- Allow public read access to DID public keys for verification
CREATE POLICY did_public_keys_read ON did_public_keys
  FOR SELECT USING (true);

-- RBAC: Allow agents to manage their own verified roles
CREATE POLICY verified_roles_own ON verified_roles
  FOR ALL USING (agent_id = current_setting('phlow.agent_id', true));

-- RBAC: Allow services to read verified roles for authorization
-- Restrict to agents that can prove they need the role information
CREATE POLICY verified_roles_service_read ON verified_roles
  FOR SELECT USING (
    -- Only allow reading roles during active authentication flows
    -- In production, this should be further restricted to specific service roles
    current_setting('phlow.authenticating_agent_id', true) IS NOT NULL
    OR agent_id = current_setting('phlow.agent_id', true)
  );

-- Function to update the updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ language 'plpgsql';

-- Triggers to auto-update the updated_at column
CREATE TRIGGER update_agent_cards_updated_at
  BEFORE UPDATE ON agent_cards
  FOR EACH ROW
  EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_did_public_keys_updated_at
  BEFORE UPDATE ON did_public_keys
  FOR EACH ROW
  EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_verified_roles_updated_at
  BEFORE UPDATE ON verified_roles
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
