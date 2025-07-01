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
        agent_id: agentCard.agentId,
        name: agentCard.name,
        description: agentCard.description,
        permissions: agentCard.permissions,
        public_key: agentCard.publicKey,
        endpoints: agentCard.endpoints,
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
      agentId: data.agent_id,
      name: data.name,
      description: data.description,
      permissions: data.permissions || [],
      publicKey: data.public_key,
      endpoints: data.endpoints,
      metadata: data.metadata,
    };
  }

  async listAgentCards(filters?: {
    permissions?: string[];
    metadata?: Record<string, any>;
  }): Promise<AgentCard[]> {
    let query = this.supabase.from('agent_cards').select('*');

    if (filters?.permissions && filters.permissions.length > 0) {
      query = query.contains('permissions', filters.permissions);
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
      agentId: item.agent_id,
      name: item.name,
      description: item.description,
      permissions: item.permissions || [],
      publicKey: item.public_key,
      endpoints: item.endpoints,
      metadata: item.metadata,
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