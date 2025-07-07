import { A2AServer, A2AContext, AgentCard as A2AAgentCard } from '@a2a-js/sdk';
import { createClient, SupabaseClient } from '@supabase/supabase-js';
import { PhlowConfig, PhlowContext, MiddlewareFunction } from './types';
import { ConfigurationError } from './errors';

export class PhlowMiddleware extends A2AServer {
  private supabase: SupabaseClient;
  private config: PhlowConfig;

  constructor(config: PhlowConfig) {
    // Initialize A2A server with agent card
    super({
      agentCard: config.agentCard as A2AAgentCard,
      privateKey: config.privateKey,
      // A2A SDK handles JWT validation internally
    });

    this.validateConfig(config);
    this.config = config;
    this.supabase = createClient(config.supabaseUrl, config.supabaseAnonKey);

    // Set up Supabase integration hooks
    this.setupSupabaseHooks();
  }

  private validateConfig(config: PhlowConfig): void {
    if (!config.supabaseUrl || !config.supabaseAnonKey) {
      throw new ConfigurationError('Supabase URL and anon key are required');
    }
  }

  private setupSupabaseHooks(): void {
    // Override A2A's onAuthenticated hook to add Supabase features
    this.on('authenticated', async (context: A2AContext) => {
      // Log authentication event to Supabase
      if (this.config.enableAuditLog) {
        await this.logAuthEvent(context);
      }

      // Attach Supabase client to context for downstream use
      (context as any).supabase = this.supabase;
    });

    // Override agent card lookup to use Supabase
    this.on('agentLookup', async (agentId: string) => {
      return await this.getAgentCardFromSupabase(agentId);
    });
  }

  private async logAuthEvent(context: A2AContext): Promise<void> {
    try {
      await this.supabase.from('auth_audit_log').insert({
        agent_id: context.agent.metadata?.agentId,
        timestamp: new Date().toISOString(),
        event_type: 'authentication',
        success: true,
        metadata: {
          skills: context.agent.skills,
          service_url: context.agent.serviceUrl,
        },
      });
    } catch (error) {
      console.error('Failed to log auth event:', error);
    }
  }

  private async getAgentCardFromSupabase(agentId: string): Promise<A2AAgentCard | null> {
    try {
      const { data, error } = await this.supabase
        .from('agent_cards')
        .select('*')
        .eq('agent_id', agentId)
        .single();

      if (error || !data) {
        return null;
      }

      // Return A2A-compliant agent card
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
    } catch (error) {
      console.error('Error fetching agent card:', error);
      return null;
    }
  }

  // Phlow-specific middleware that wraps A2A authentication
  public authenticate(): MiddlewareFunction {
    return async (req: any, res: any, next: (error?: any) => void) => {
      try {
        // Let A2A SDK handle the authentication
        const a2aMiddleware = this.getAuthMiddleware();
        await a2aMiddleware(req, res, (err?: any) => {
          if (err) {
            return next(err);
          }

          // Add Phlow-specific context
          const a2aContext = (req as any).a2a;
          if (a2aContext) {
            const phlowContext: PhlowContext = {
              agent: a2aContext.agent,
              token: a2aContext.token,
              claims: a2aContext.claims,
              supabase: this.supabase,
            };
            (req as any).phlow = phlowContext;
          }

          next();
        });
      } catch (error) {
        next(error);
      }
    };
  }

  // Supabase-specific helpers
  public getSupabaseClient(): SupabaseClient {
    return this.supabase;
  }

  // RLS policy generator for Supabase
  public generateRLSPolicy(agentId: string, permissions: string[]): string {
    const permissionChecks = permissions
      .map(p => `auth.jwt() ->> 'permissions' ? '${p}'`)
      .join(' OR ');

    return `
      CREATE POLICY "${agentId}_policy" ON your_table
      FOR ALL
      TO authenticated
      USING (
        auth.jwt() ->> 'sub' = '${agentId}'
        AND (${permissionChecks})
      );
    `;
  }

  // Helper to register agent in Supabase
  public async registerAgent(agentCard: A2AAgentCard): Promise<void> {
    const { error } = await this.supabase.from('agent_cards').upsert({
      agent_id: agentCard.metadata?.agentId,
      name: agentCard.name,
      description: agentCard.description,
      service_url: agentCard.serviceUrl,
      schema_version: agentCard.schemaVersion,
      skills: agentCard.skills,
      security_schemes: agentCard.securitySchemes,
      public_key: agentCard.metadata?.publicKey,
      metadata: agentCard.metadata,
      created_at: new Date().toISOString(),
    });

    if (error) {
      throw new Error(`Failed to register agent: ${error.message}`);
    }
  }
}