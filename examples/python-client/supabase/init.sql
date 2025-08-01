-- Phlow Database Schema Initialization
-- This script sets up the necessary tables and functions for Phlow authentication

-- Enable necessary extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Create agent_cards table
CREATE TABLE IF NOT EXISTS public.agent_cards (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    agent_id TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    description TEXT DEFAULT '',
    service_url TEXT DEFAULT '',
    skills JSONB DEFAULT '[]'::jsonb,
    security_schemes JSONB DEFAULT '{}'::jsonb,
    metadata JSONB DEFAULT '{}'::jsonb,
    public_key TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create audit_logs table for tracking authentication events
CREATE TABLE IF NOT EXISTS public.audit_logs (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    agent_id TEXT NOT NULL,
    event_type TEXT NOT NULL, -- 'auth_success', 'auth_failure', 'token_issued', etc.
    event_data JSONB DEFAULT '{}'::jsonb,
    ip_address INET,
    user_agent TEXT,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create rate_limits table for rate limiting
CREATE TABLE IF NOT EXISTS public.rate_limits (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    agent_id TEXT NOT NULL,
    endpoint TEXT NOT NULL,
    request_count INTEGER DEFAULT 0,
    window_start TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(agent_id, endpoint, window_start)
);

-- Create updated_at trigger function
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Add updated_at trigger to agent_cards
DROP TRIGGER IF EXISTS update_agent_cards_updated_at ON public.agent_cards;
CREATE TRIGGER update_agent_cards_updated_at
    BEFORE UPDATE ON public.agent_cards
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_agent_cards_agent_id ON public.agent_cards(agent_id);
CREATE INDEX IF NOT EXISTS idx_audit_logs_agent_id ON public.audit_logs(agent_id);
CREATE INDEX IF NOT EXISTS idx_audit_logs_timestamp ON public.audit_logs(timestamp);
CREATE INDEX IF NOT EXISTS idx_rate_limits_agent_endpoint ON public.rate_limits(agent_id, endpoint);
CREATE INDEX IF NOT EXISTS idx_rate_limits_window_start ON public.rate_limits(window_start);

-- Insert sample agent card for testing
INSERT INTO public.agent_cards (
    agent_id,
    name,
    description,
    service_url,
    skills,
    metadata,
    public_key
) VALUES (
    'python-agent-001',
    'Python Agent Example',
    'A Python-based Phlow agent using FastAPI',
    'http://localhost:8000',
    '["read:data", "write:data"]'::jsonb,
    '{"language": "python", "framework": "fastapi", "version": "1.0.0"}'::jsonb,
    '-----BEGIN PUBLIC KEY-----
MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEA4f3e1nkbHm+9lqK5P8xJ
-----END PUBLIC KEY-----'
) ON CONFLICT (agent_id) DO UPDATE SET
    name = EXCLUDED.name,
    description = EXCLUDED.description,
    service_url = EXCLUDED.service_url,
    skills = EXCLUDED.skills,
    metadata = EXCLUDED.metadata,
    public_key = EXCLUDED.public_key,
    updated_at = NOW();

-- Create necessary roles for PostgreSQL (in Supabase these exist by default)
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'anon') THEN
        CREATE ROLE anon;
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'authenticated') THEN
        CREATE ROLE authenticated;
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'authenticator') THEN
        CREATE ROLE authenticator LOGIN;
        GRANT anon TO authenticator;
        GRANT authenticated TO authenticator;
    END IF;
END
$$;

-- Grant necessary permissions
GRANT USAGE ON SCHEMA public TO anon, authenticated;
GRANT SELECT ON public.agent_cards TO anon, authenticated;
GRANT SELECT, INSERT, UPDATE ON public.audit_logs TO authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON public.rate_limits TO authenticated;

-- Row Level Security policies (basic setup)
ALTER TABLE public.agent_cards ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.audit_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.rate_limits ENABLE ROW LEVEL SECURITY;

-- Allow reading agent cards (public information)
CREATE POLICY IF NOT EXISTS "Agent cards are viewable by everyone" 
ON public.agent_cards FOR SELECT 
USING (true);

-- Allow authenticated users to manage their own audit logs
CREATE POLICY IF NOT EXISTS "Users can view own audit logs" 
ON public.audit_logs FOR SELECT 
USING (auth.uid()::text = agent_id OR auth.role() = 'service_role');

CREATE POLICY IF NOT EXISTS "Users can insert own audit logs" 
ON public.audit_logs FOR INSERT 
WITH CHECK (auth.uid()::text = agent_id OR auth.role() = 'service_role');

-- Allow authenticated users to manage their own rate limits
CREATE POLICY IF NOT EXISTS "Users can manage own rate limits" 
ON public.rate_limits FOR ALL 
USING (auth.uid()::text = agent_id OR auth.role() = 'service_role');

-- Create a function to clean up old audit logs (optional)
CREATE OR REPLACE FUNCTION cleanup_old_audit_logs()
RETURNS void AS $$
BEGIN
    DELETE FROM public.audit_logs 
    WHERE timestamp < NOW() - INTERVAL '30 days';
END;
$$ LANGUAGE plpgsql;

-- Create a function to reset rate limits (optional)
CREATE OR REPLACE FUNCTION reset_expired_rate_limits()
RETURNS void AS $$
BEGIN
    DELETE FROM public.rate_limits 
    WHERE window_start < NOW() - INTERVAL '1 hour';
END;
$$ LANGUAGE plpgsql;

NOTIFY pgrst, 'reload schema';