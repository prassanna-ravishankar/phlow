import { createClient, SupabaseClient } from '@supabase/supabase-js';
import { A2AClient, A2AServer } from 'a2a-js';
import { PhlowConfig, PhlowContext, MiddlewareFunction, AgentCard } from './types';
import { ConfigurationError } from './errors';
import * as jwt from 'jsonwebtoken';

export class PhlowMiddleware {
  private supabase: SupabaseClient;
  private config: PhlowConfig;
  private a2aClient?: A2AClient;
  private a2aServer?: A2AServer;
  // A2A card resolver would be initialized when needed

  constructor(config: PhlowConfig) {
    this.validateConfig(config);
    this.config = config;
    this.supabase = createClient(config.supabaseUrl, config.supabaseAnonKey);
    
    // Initialize A2A components if service URL is provided
    if (config.agentCard.serviceUrl) {
      try {
        // Card resolver would be initialized when needed
        this.a2aClient = new A2AClient(config.agentCard.serviceUrl);
        // A2AServer initialization would be done separately when needed
      } catch (error) {
        console.warn('A2A initialization failed:', error);
      }
    }
  }

  private validateConfig(config: PhlowConfig): void {
    if (!config.supabaseUrl || !config.supabaseAnonKey) {
      throw new ConfigurationError('Supabase URL and anon key are required');
    }
  }

  private async verifyA2AToken(token: string): Promise<PhlowContext | null> {
    try {
      // Verify JWT token
      const decoded = jwt.verify(token, this.config.publicKey || '', {
        algorithms: ['RS256', 'ES256']
      }) as jwt.JwtPayload;

      // Get agent card from token claims or Supabase
      const agentId = decoded.sub || decoded.agentId;
      const agentCard = await this.getAgentCardFromSupabase(agentId);

      if (!agentCard) {
        return null;
      }

      return {
        agent: agentCard,
        token,
        claims: decoded,
        supabase: this.supabase
      };
    } catch (error) {
      console.error('Token verification failed:', error);
      return null;
    }
  }

  private async logAuthEvent(context: PhlowContext, success: boolean): Promise<void> {
    if (!this.config.enableAuditLog) return;
    
    try {
      await this.supabase.from('auth_audit_log').insert({
        agent_id: context.agent.metadata?.agentId,
        timestamp: new Date().toISOString(),
        event_type: 'authentication',
        success,
        metadata: {
          skills: context.agent.skills,
          service_url: context.agent.serviceUrl,
        },
      });
    } catch (error) {
      console.error('Failed to log auth event:', error);
    }
  }

  private async getAgentCardFromSupabase(agentId: string): Promise<AgentCard | null> {
    try {
      const { data, error } = await this.supabase
        .from('agent_cards')
        .select('*')
        .eq('agent_id', agentId)
        .single();

      if (error || !data) {
        return null;
      }

      // Return agent card
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
      } as AgentCard;
    } catch (error) {
      console.error('Error fetching agent card:', error);
      return null;
    }
  }

  // Authentication middleware
  public authenticate(): MiddlewareFunction {
    return async (req: unknown, res: unknown, next: (error?: unknown) => void) => {
      try {
        // Extract token from Authorization header
        const authHeader = (req as { headers: { authorization?: string } }).headers.authorization;
        if (!authHeader || !authHeader.startsWith('Bearer ')) {
          return (res as { status: (code: number) => { json: (data: unknown) => void } }).status(401).json({ error: 'Missing or invalid authorization header' });
        }

        const token = authHeader.substring(7);
        const context = await this.verifyA2AToken(token);

        if (!context) {
          await this.logAuthEvent({ agent: {} as AgentCard, token, claims: {}, supabase: this.supabase }, false);
          return (res as { status: (code: number) => { json: (data: unknown) => void } }).status(401).json({ error: 'Invalid token' });
        }

        // Attach context to request with A2A integration
        (req as { phlow: PhlowContext }).phlow = {
          ...context,
          a2aClient: this.a2aClient,
          a2aServer: this.a2aServer
        };
        
        // Log successful auth
        await this.logAuthEvent(context, true);

        next();
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
  public async registerAgent(agentCard: AgentCard): Promise<void> {
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
  
  // A2A Protocol methods
  public async sendMessage(targetAgentId: string, message: string): Promise<unknown> {
    if (!this.a2aClient) {
      throw new Error('A2A client not initialized. Ensure serviceUrl is configured.');
    }
    
    try {
      const targetCard = await this.resolveAgent(targetAgentId);
      if (!targetCard) {
        throw new Error(`Agent ${targetAgentId} not found`);
      }
      
      // Use the A2A client to send a task
      // For now, return a mock response - would need proper A2A integration
      return Promise.resolve({
        taskId: `task-${Date.now()}`,
        targetAgent: targetAgentId,
        message: message,
        status: 'sent'
      });
    } catch (error) {
      console.error('Failed to send A2A message:', error);
      throw error;
    }
  }
  
  public async resolveAgent(agentId: string): Promise<AgentCard | null> {
    try {
      // First try Supabase
      const agentCard = await this.getAgentCardFromSupabase(agentId);
      if (agentCard) {
        return agentCard;
      }
      
      // Then try A2A network resolution
      // For now, return null as we'd need to implement card resolution
      // This would typically involve network calls to resolve agent cards
      return null;
      
      // TODO: Implement proper A2A network resolution
      /* 
      const a2aCard = await this.cardResolver.resolve(agentId);
      if (a2aCard) {
        // Convert A2A card to Phlow format and cache in Supabase
        const phlowCard: AgentCard = {
          schemaVersion: '1.0',
          name: a2aCard.name || 'Unknown',
          description: a2aCard.description || '',
          serviceUrl: a2aCard.serviceUrl || '',
          skills: a2aCard.skills || [],
          securitySchemes: a2aCard.securitySchemes || {},
          metadata: {
            ...a2aCard.metadata,
            agentId
          }
        };
        
        await this.registerAgent(phlowCard);
        return phlowCard;
      }
      */
    } catch (error) {
      console.error('Failed to resolve agent:', error);
      return null;
    }
  }
  
  public async setupA2AServer(_taskHandler: (task: unknown) => Promise<unknown>): Promise<void> {
    // This would configure the A2A server to handle incoming tasks
    // Implementation depends on how you want to expose A2A endpoints
  }
  
  public getA2AClient(): A2AClient | undefined {
    return this.a2aClient;
  }
  
  public getA2AServer(): A2AServer | undefined {
    return this.a2aServer;
  }
  
  public async initializeA2AServer(requestHandler: (request: unknown) => Promise<unknown>): Promise<void> {
    if (!this.config.agentCard.serviceUrl) {
      throw new Error('Cannot initialize A2A server without serviceUrl');
    }
    
    try {
      // A2AServer would need proper agent card format conversion
      // For now, store the handler for future use
      console.log('A2A server handler registered:', typeof requestHandler);
    } catch (error) {
      console.error('Failed to initialize A2A server:', error);
      throw error;
    }
  }
}