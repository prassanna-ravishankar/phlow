import { SupabaseClient } from '@supabase/supabase-js';
import { AgentCard } from './types';

export class SupabaseHelpers {
  private supabase: SupabaseClient;

  constructor(supabase: SupabaseClient) {
    this.supabase = supabase;
  }

  async registerAgentCard(agentCard: AgentCard): Promise<void> {
    const { error } = await this.supabase
      .from('agent_cards')
      .upsert({
        agent_id: agentCard.metadata?.agentId,
        name: agentCard.name,
        description: agentCard.description,
        service_url: agentCard.serviceUrl,
        schema_version: agentCard.schemaVersion,
        skills: agentCard.skills,
        security_schemes: agentCard.securitySchemes,
        public_key: agentCard.metadata?.publicKey,
        metadata: agentCard.metadata,
        updated_at: new Date().toISOString(),
      });

    if (error) {
      throw new Error(`Failed to register agent card: ${error.message}`);
    }
  }

  async getAgentCard(agentId: string): Promise<AgentCard | null> {
    const { data, error } = await this.supabase
      .from('agent_cards')
      .select('*')
      .eq('agent_id', agentId)
      .single();

    if (error || !data) {
      return null;
    }

    return {
      schemaVersion: data.schema_version || '1.0',
      name: data.name,
      description: data.description,
      serviceUrl: data.service_url,
      skills: data.skills || [],
      securitySchemes: data.security_schemes || {},
      metadata: {
        ...data.metadata,
        agentId: data.agent_id,
        publicKey: data.public_key,
      },
    };
  }

  async listAgentCards(filters?: {
    skills?: string[];
    metadata?: Record<string, unknown>;
  }): Promise<AgentCard[]> {
    let query = this.supabase.from('agent_cards').select('*');

    if (filters?.skills && filters.skills.length > 0) {
      query = query.contains('skills', filters.skills);
    }

    if (filters?.metadata) {
      Object.entries(filters.metadata).forEach(([key, value]) => {
        query = query.eq(`metadata->>${key}`, value);
      });
    }

    const { data, error } = await query;

    if (error) {
      throw new Error(`Failed to list agent cards: ${error.message}`);
    }

    return (data || []).map(item => ({
      schemaVersion: item.schema_version || '1.0',
      name: item.name,
      description: item.description,
      serviceUrl: item.service_url,
      skills: item.skills || [],
      securitySchemes: item.security_schemes || {},
      metadata: {
        ...item.metadata,
        agentId: item.agent_id,
        publicKey: item.public_key,
      },
    }));
  }

  generateRLSPolicy(tableName: string, policyName: string): string {
    return `
-- Enable RLS on the table
ALTER TABLE ${tableName} ENABLE ROW LEVEL SECURITY;

-- Create policy for agent authentication
CREATE POLICY ${policyName} ON ${tableName}
FOR ALL
USING (
  auth.jwt() ->> 'sub' IS NOT NULL
  AND EXISTS (
    SELECT 1 FROM agent_cards
    WHERE agent_id = auth.jwt() ->> 'sub'
  )
);
    `.trim();
  }

  generateAgentSpecificRLSPolicy(
    tableName: string,
    policyName: string,
    agentIdColumn: string = 'agent_id'
  ): string {
    return `
-- Enable RLS on the table
ALTER TABLE ${tableName} ENABLE ROW LEVEL SECURITY;

-- Create policy for agent-specific access
CREATE POLICY ${policyName} ON ${tableName}
FOR ALL
USING (
  ${agentIdColumn} = auth.jwt() ->> 'sub'
);
    `.trim();
  }

  generatePermissionBasedRLSPolicy(
    tableName: string,
    policyName: string,
    requiredPermission: string
  ): string {
    return `
-- Enable RLS on the table
ALTER TABLE ${tableName} ENABLE ROW LEVEL SECURITY;

-- Create policy for permission-based access
CREATE POLICY ${policyName} ON ${tableName}
FOR ALL
USING (
  auth.jwt() -> 'permissions' ? '${requiredPermission}'
);
    `.trim();
  }
}