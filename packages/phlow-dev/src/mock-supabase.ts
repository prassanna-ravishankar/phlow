import { AgentCard } from 'phlow-auth';

export interface MockSupabaseConfig {
  agents: AgentCard[];
  enableAuditLogs?: boolean;
}

export class MockSupabase {
  private agents: Map<string, AgentCard> = new Map();
  private auditLogs: any[] = [];
  private enableAuditLogs: boolean;

  constructor(config: MockSupabaseConfig) {
    this.enableAuditLogs = config.enableAuditLogs || false;
    
    // Populate initial agents
    config.agents.forEach(agent => {
      this.agents.set(agent.agentId, agent);
    });
  }

  // Mock Supabase client methods
  from(table: string) {
    if (table === 'agent_cards') {
      return {
        select: (columns: string) => ({
          eq: (column: string, value: string) => ({
            single: () => {
              const agent = this.agents.get(value);
              return Promise.resolve({
                data: agent ? {
                  agent_id: agent.agentId,
                  name: agent.name,
                  description: agent.description,
                  permissions: agent.permissions,
                  public_key: agent.publicKey,
                  endpoints: agent.endpoints,
                  metadata: agent.metadata,
                } : null,
                error: agent ? null : { message: 'Agent not found' },
              });
            },
          }),
        }),
        upsert: (data: any) => {
          const agent: AgentCard = {
            agentId: data.agent_id,
            name: data.name,
            description: data.description,
            permissions: data.permissions || [],
            publicKey: data.public_key,
            endpoints: data.endpoints,
            metadata: data.metadata,
          };
          
          this.agents.set(agent.agentId, agent);
          
          return Promise.resolve({
            data: data,
            error: null,
          });
        },
      };
    }

    if (table === 'phlow_audit_logs') {
      return {
        insert: (logs: any[]) => {
          if (this.enableAuditLogs) {
            this.auditLogs.push(...logs);
          }
          return Promise.resolve({
            data: logs,
            error: null,
          });
        },
      };
    }

    return {
      select: () => ({ data: [], error: null }),
      insert: () => ({ data: [], error: null }),
      upsert: () => ({ data: [], error: null }),
    };
  }

  // Helper methods for testing
  getAgent(agentId: string): AgentCard | undefined {
    return this.agents.get(agentId);
  }

  getAllAgents(): AgentCard[] {
    return Array.from(this.agents.values());
  }

  getAuditLogs(): any[] {
    return [...this.auditLogs];
  }

  clearAuditLogs(): void {
    this.auditLogs = [];
  }

  addAgent(agent: AgentCard): void {
    this.agents.set(agent.agentId, agent);
  }

  removeAgent(agentId: string): void {
    this.agents.delete(agentId);
  }

  reset(): void {
    this.agents.clear();
    this.auditLogs = [];
  }
}

export function createMockSupabase(config: MockSupabaseConfig): MockSupabase {
  return new MockSupabase(config);
}