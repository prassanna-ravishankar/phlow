# Database Schema

This guide covers the Supabase database schema used by Phlow for agent card storage, Row Level Security (RLS) policies, and data management patterns.

## Overview

Phlow uses **Supabase** as its backend registry for:
- **Agent Cards** - Public keys and metadata storage
- **Authentication** - JWT verification and agent lookup
- **Security** - Row Level Security policies for multi-tenant access
- **Audit Trails** - Request logging and compliance (planned)

## Core Tables

### agent_cards

The primary table storing agent information and public keys.

```sql
CREATE TABLE agent_cards (
  -- Primary identification
  agent_id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  description TEXT,
  
  -- Authentication
  public_key TEXT NOT NULL,
  service_url TEXT,
  
  -- A2A Protocol fields
  schema_version TEXT DEFAULT '1.0',
  permissions JSONB DEFAULT '[]'::jsonb,
  skills JSONB DEFAULT '[]'::jsonb,
  security_schemes JSONB DEFAULT '{}'::jsonb,
  endpoints JSONB DEFAULT '{}'::jsonb,
  metadata JSONB DEFAULT '{}'::jsonb,
  
  -- Housekeeping
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  
  -- Constraints
  CONSTRAINT agent_cards_agent_id_check CHECK (length(agent_id) > 0),
  CONSTRAINT agent_cards_name_check CHECK (length(name) > 0),
  CONSTRAINT agent_cards_public_key_check CHECK (
    public_key LIKE '%BEGIN PUBLIC KEY%' OR 
    public_key LIKE '%BEGIN RSA PUBLIC KEY%'
  )
);
```

#### Indexes

```sql
-- Primary lookup by agent_id (automatic via PRIMARY KEY)

-- Search by permissions
CREATE INDEX idx_agent_cards_permissions ON agent_cards 
USING GIN (permissions);

-- Search by skills
CREATE INDEX idx_agent_cards_skills ON agent_cards 
USING GIN (skills);

-- Search by metadata
CREATE INDEX idx_agent_cards_metadata ON agent_cards 
USING GIN (metadata);

-- Service URL lookup
CREATE INDEX idx_agent_cards_service_url ON agent_cards (service_url)
WHERE service_url IS NOT NULL;

-- Updated timestamp for cache invalidation
CREATE INDEX idx_agent_cards_updated_at ON agent_cards (updated_at);
```

#### Example Data

```sql
INSERT INTO agent_cards (
  agent_id,
  name,
  description,
  public_key,
  service_url,
  permissions,
  skills,
  endpoints,
  metadata
) VALUES (
  'data-analyzer-v1',
  'Data Analysis Agent',
  'Specialized agent for statistical analysis and data processing',
  '-----BEGIN PUBLIC KEY-----
MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEA...
-----END PUBLIC KEY-----',
  'https://data-analyzer.example.com',
  '["read:data", "write:analysis", "read:public"]'::jsonb,
  '[
    {"name": "statistical-analysis", "description": "Perform statistical analysis"},
    {"name": "data-visualization", "description": "Generate charts and graphs"},
    {"name": "data-cleaning", "description": "Clean and preprocess data"}
  ]'::jsonb,
  '{
    "analyze": {"method": "POST", "path": "/analyze", "description": "Analyze dataset"},
    "visualize": {"method": "POST", "path": "/visualize", "description": "Create visualization"}
  }'::jsonb,
  '{
    "version": "1.2.0",
    "region": "us-west-2",
    "max_dataset_size": "10GB",
    "supported_formats": ["csv", "json", "parquet"]
  }'::jsonb
);
```

### JSONB Field Schemas

#### permissions
Array of permission strings in `action:resource` format:
```json
[
  "read:data",
  "write:analysis", 
  "admin:users",
  "execute:model"
]
```

#### skills
Array of skill objects with name and optional description:
```json
[
  {
    "name": "data-analysis",
    "description": "Statistical and analytical processing of datasets"
  },
  {
    "name": "machine-learning", 
    "description": "Training and inference with ML models"
  }
]
```

#### security_schemes
Authentication schemes supported by the agent:
```json
{
  "bearer": {
    "type": "bearer",
    "scheme": "bearer"
  },
  "apiKey": {
    "type": "apiKey",
    "in": "header",
    "name": "X-API-Key"
  }
}
```

#### endpoints
Available API endpoints:
```json
{
  "analyze": {
    "method": "POST",
    "path": "/analyze",
    "description": "Analyze data with specified parameters"
  },
  "health": {
    "method": "GET", 
    "path": "/health",
    "description": "Health check endpoint"
  }
}
```

#### metadata
Custom metadata specific to the agent:
```json
{
  "version": "2.1.0",
  "region": "us-east-1",
  "contact": "admin@example.com",
  "sla": {
    "uptime": "99.9%",
    "response_time": "< 200ms"
  }
}
```

## Row Level Security (RLS)

Supabase RLS policies provide secure, multi-tenant access control.

### Enable RLS

```sql
ALTER TABLE agent_cards ENABLE ROW LEVEL SECURITY;
```

### Policy Types

#### 1. Public Read Access
Allow anyone to read agent cards for discovery:

```sql
CREATE POLICY "public_read_agent_cards" ON agent_cards
FOR SELECT
USING (true);
```

#### 2. Authenticated Agent Access
Only authenticated agents can read agent cards:

```sql
CREATE POLICY "authenticated_read_agent_cards" ON agent_cards
FOR SELECT
USING (
  -- Check if the JWT contains a valid agent ID
  auth.jwt() ->> 'sub' IS NOT NULL
  AND EXISTS (
    SELECT 1 FROM agent_cards 
    WHERE agent_id = auth.jwt() ->> 'sub'
  )
);
```

#### 3. Agent Self-Management
Agents can only modify their own records:

```sql
CREATE POLICY "agent_self_management" ON agent_cards
FOR ALL
USING (
  auth.jwt() ->> 'sub' = agent_id
);
```

#### 4. Permission-Based Access
Access based on JWT permissions:

```sql
CREATE POLICY "permission_based_read" ON agent_cards
FOR SELECT
USING (
  -- Allow if JWT contains 'read:agents' permission
  auth.jwt() -> 'permissions' ? 'read:agents'
);

CREATE POLICY "admin_full_access" ON agent_cards
FOR ALL
USING (
  -- Allow full access for admin agents
  auth.jwt() -> 'permissions' ? 'admin:agents'
);
```

#### 5. Metadata-Based Access
Access based on agent metadata:

```sql
CREATE POLICY "region_based_access" ON agent_cards
FOR SELECT
USING (
  -- Only allow access to agents in the same region
  metadata ->> 'region' = (auth.jwt() -> 'metadata' ->> 'region')
);
```

### Policy Generation Helpers

Both JavaScript and Python implementations provide RLS policy generation:

**JavaScript**:
```typescript
import { SupabaseHelpers } from 'phlow-auth'

// Generate basic authentication policy
const policy = SupabaseHelpers.generateRLSPolicy(
  'protected_data',
  'agent_access',
  'basic_auth'
)

console.log(policy)
```

**Python**:
```python
from phlow.supabase_helpers import SupabaseHelpers

# Generate permission-based policy
policy = SupabaseHelpers.generate_rls_policy(
    'sensitive_data',
    'permission_check',
    'permission_based'
)

print(policy)
```

## Advanced Queries

### Agent Discovery

**Find agents by skills**:
```sql
SELECT agent_id, name, skills
FROM agent_cards
WHERE skills @> '[{"name": "data-analysis"}]';
```

**Find agents by permissions**:
```sql
SELECT agent_id, name, permissions
FROM agent_cards  
WHERE permissions ? 'read:data';
```

**Complex metadata search**:
```sql
SELECT agent_id, name, metadata
FROM agent_cards
WHERE metadata ->> 'region' = 'us-west-2'
  AND (metadata -> 'sla' ->> 'uptime')::FLOAT > 99.0;
```

### Performance Optimization

**Agent card with skills lookup**:
```sql
-- Optimized query using GIN indexes
SELECT ac.*, 
       COALESCE(ac.skills, '[]'::jsonb) as skills
FROM agent_cards ac
WHERE ac.skills @> $1::jsonb  -- Uses GIN index
  AND ac.permissions ? ANY($2::text[]);  -- Uses GIN index
```

**Batch agent lookup**:
```sql
-- Efficient batch lookup for multiple agents
SELECT agent_id, name, public_key, permissions
FROM agent_cards
WHERE agent_id = ANY($1::text[])
ORDER BY array_position($1::text[], agent_id);
```

## Database Functions

### Agent Card Management

```sql
-- Function to safely update agent card
CREATE OR REPLACE FUNCTION update_agent_card(
  p_agent_id TEXT,
  p_name TEXT DEFAULT NULL,
  p_description TEXT DEFAULT NULL,
  p_public_key TEXT DEFAULT NULL,
  p_service_url TEXT DEFAULT NULL,
  p_permissions JSONB DEFAULT NULL,
  p_skills JSONB DEFAULT NULL,
  p_endpoints JSONB DEFAULT NULL,
  p_metadata JSONB DEFAULT NULL
)
RETURNS agent_cards
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
  result agent_cards;
BEGIN
  UPDATE agent_cards SET
    name = COALESCE(p_name, name),
    description = COALESCE(p_description, description),
    public_key = COALESCE(p_public_key, public_key),
    service_url = COALESCE(p_service_url, service_url),
    permissions = COALESCE(p_permissions, permissions),
    skills = COALESCE(p_skills, skills),
    endpoints = COALESCE(p_endpoints, endpoints),
    metadata = COALESCE(p_metadata, metadata),
    updated_at = NOW()
  WHERE agent_id = p_agent_id
  RETURNING * INTO result;
  
  IF NOT FOUND THEN
    RAISE EXCEPTION 'Agent card not found: %', p_agent_id;
  END IF;
  
  RETURN result;
END;
$$;
```

### Search Functions

```sql
-- Advanced agent search function
CREATE OR REPLACE FUNCTION search_agents(
  p_skills TEXT[] DEFAULT NULL,
  p_permissions TEXT[] DEFAULT NULL,
  p_metadata JSONB DEFAULT NULL,
  p_limit INT DEFAULT 50,
  p_offset INT DEFAULT 0
)
RETURNS TABLE (
  agent_id TEXT,
  name TEXT,
  description TEXT,
  skills JSONB,
  permissions JSONB,
  metadata JSONB,
  match_score FLOAT
)
LANGUAGE plpgsql
AS $$
BEGIN
  RETURN QUERY
  SELECT 
    ac.agent_id,
    ac.name,
    ac.description,
    ac.skills,
    ac.permissions,
    ac.metadata,
    -- Calculate relevance score
    (
      CASE WHEN p_skills IS NOT NULL THEN
        (SELECT COUNT(*) FROM unnest(p_skills) skill 
         WHERE ac.skills @> jsonb_build_array(jsonb_build_object('name', skill)))
      ELSE 0 END +
      CASE WHEN p_permissions IS NOT NULL THEN
        (SELECT COUNT(*) FROM unnest(p_permissions) perm WHERE ac.permissions ? perm)
      ELSE 0 END
    )::FLOAT as match_score
  FROM agent_cards ac
  WHERE 
    (p_skills IS NULL OR ac.skills @> (
      SELECT jsonb_agg(jsonb_build_object('name', skill))
      FROM unnest(p_skills) skill
    )) AND
    (p_permissions IS NULL OR ac.permissions ?& p_permissions) AND
    (p_metadata IS NULL OR ac.metadata @> p_metadata)
  ORDER BY match_score DESC, ac.name
  LIMIT p_limit
  OFFSET p_offset;
END;
$$;
```

## Audit and Logging Schema

### auth_events (Planned)

```sql
CREATE TABLE auth_events (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  agent_id TEXT NOT NULL,
  event_type TEXT NOT NULL CHECK (event_type IN ('auth_attempt', 'permission_check', 'token_refresh')),
  success BOOLEAN NOT NULL,
  error_code TEXT,
  error_message TEXT,
  ip_address INET,
  user_agent TEXT,
  permissions TEXT[],
  metadata JSONB DEFAULT '{}'::jsonb,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes for audit queries
CREATE INDEX idx_auth_events_agent_id ON auth_events (agent_id);
CREATE INDEX idx_auth_events_created_at ON auth_events (created_at);
CREATE INDEX idx_auth_events_success ON auth_events (success);
CREATE INDEX idx_auth_events_event_type ON auth_events (event_type);

-- Partition by month for performance
CREATE TABLE auth_events_y2024m01 PARTITION OF auth_events
FOR VALUES FROM ('2024-01-01') TO ('2024-02-01');
```

### rate_limits (Planned)

```sql
CREATE TABLE rate_limits (
  key TEXT PRIMARY KEY,
  count INTEGER NOT NULL DEFAULT 0,
  window_start TIMESTAMP WITH TIME ZONE NOT NULL,
  window_end TIMESTAMP WITH TIME ZONE NOT NULL,
  max_requests INTEGER NOT NULL,
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- TTL index for automatic cleanup
CREATE INDEX idx_rate_limits_window_end ON rate_limits (window_end);
```

## Database Maintenance

### Automated Updates

```sql
-- Trigger to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_agent_cards_updated_at 
  BEFORE UPDATE ON agent_cards
  FOR EACH ROW 
  EXECUTE FUNCTION update_updated_at_column();
```

### Data Validation

```sql
-- Additional constraints for data quality
ALTER TABLE agent_cards ADD CONSTRAINT agent_cards_permissions_format
CHECK (
  permissions IS NULL OR (
    jsonb_typeof(permissions) = 'array' AND
    (SELECT bool_and(value::text ~ '^"[a-z][a-z0-9_]*:[a-z][a-z0-9_]*"$')
     FROM jsonb_array_elements(permissions))
  )
);

ALTER TABLE agent_cards ADD CONSTRAINT agent_cards_skills_format
CHECK (
  skills IS NULL OR (
    jsonb_typeof(skills) = 'array' AND
    (SELECT bool_and(value ? 'name' AND jsonb_typeof(value -> 'name') = 'string')
     FROM jsonb_array_elements(skills))
  )
);
```

### Backup and Recovery

```sql
-- Create backup of agent cards
CREATE TABLE agent_cards_backup AS 
SELECT * FROM agent_cards;

-- Export agent cards to JSON
COPY (
  SELECT jsonb_pretty(to_jsonb(agent_cards)) 
  FROM agent_cards
) TO '/tmp/agent_cards_backup.json';

-- Restore from backup
INSERT INTO agent_cards 
SELECT * FROM agent_cards_backup
ON CONFLICT (agent_id) DO UPDATE SET
  name = EXCLUDED.name,
  description = EXCLUDED.description,
  public_key = EXCLUDED.public_key,
  -- ... other fields
  updated_at = NOW();
```

## Migration Scripts

### Initial Setup

```sql
-- migrations/001_create_agent_cards.sql
CREATE TABLE agent_cards (
  agent_id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  description TEXT,
  public_key TEXT NOT NULL,
  service_url TEXT,
  schema_version TEXT DEFAULT '1.0',
  permissions JSONB DEFAULT '[]'::jsonb,
  skills JSONB DEFAULT '[]'::jsonb,
  security_schemes JSONB DEFAULT '{}'::jsonb,
  endpoints JSONB DEFAULT '{}'::jsonb,
  metadata JSONB DEFAULT '{}'::jsonb,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Enable RLS
ALTER TABLE agent_cards ENABLE ROW LEVEL SECURITY;

-- Create indexes
CREATE INDEX idx_agent_cards_permissions ON agent_cards USING GIN (permissions);
CREATE INDEX idx_agent_cards_skills ON agent_cards USING GIN (skills);
CREATE INDEX idx_agent_cards_metadata ON agent_cards USING GIN (metadata);
```

### Add Audit Logging

```sql
-- migrations/002_add_audit_logging.sql
CREATE TABLE auth_events (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  agent_id TEXT NOT NULL,
  event_type TEXT NOT NULL,
  success BOOLEAN NOT NULL,
  error_code TEXT,
  error_message TEXT,
  ip_address INET,
  user_agent TEXT,
  permissions TEXT[],
  metadata JSONB DEFAULT '{}'::jsonb,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_auth_events_agent_id ON auth_events (agent_id);
CREATE INDEX idx_auth_events_created_at ON auth_events (created_at);
```

## Performance Considerations

### Query Optimization

1. **Use GIN indexes** for JSONB queries
2. **Limit result sets** with LIMIT clauses
3. **Use prepared statements** for repeated queries
4. **Batch operations** when possible
5. **Monitor query performance** with EXPLAIN ANALYZE

### Connection Management

```sql
-- Supabase connection pooling configuration
-- These settings are managed by Supabase automatically
-- max_connections = 100
-- shared_preload_libraries = 'pg_stat_statements'
-- track_activity_query_size = 1024
```

### Monitoring Queries

```sql
-- Monitor slow queries
SELECT query, mean_time, calls, total_time
FROM pg_stat_statements
WHERE query LIKE '%agent_cards%'
ORDER BY mean_time DESC
LIMIT 10;

-- Check index usage
SELECT schemaname, tablename, indexname, idx_scan, idx_tup_read, idx_tup_fetch
FROM pg_stat_user_indexes
WHERE tablename = 'agent_cards';
```

---

This database schema provides a robust foundation for agent card storage and management, with comprehensive security policies and performance optimizations. The next section covers [Testing Strategy](testing-strategy.md) for ensuring database operations work correctly.