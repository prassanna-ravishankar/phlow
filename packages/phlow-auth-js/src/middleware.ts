import { createClient, SupabaseClient } from '@supabase/supabase-js';
import { PhlowConfig, PhlowContext, MiddlewareFunction, AgentCard } from './types';
import { verifyToken } from './jwt';
import { AuthenticationError, ConfigurationError } from './errors';

export class PhlowMiddleware {
  private supabase: SupabaseClient;
  private config: PhlowConfig;

  constructor(config: PhlowConfig) {
    this.validateConfig(config);
    this.config = config;
    this.supabase = createClient(config.supabaseUrl, config.supabaseAnonKey);
  }

  private validateConfig(config: PhlowConfig): void {
    if (!config.supabaseUrl || !config.supabaseAnonKey) {
      throw new ConfigurationError('Supabase URL and anon key are required');
    }
    if (!config.agentCard || !config.agentCard.agentId) {
      throw new ConfigurationError('Agent card with agentId is required');
    }
    if (!config.privateKey) {
      throw new ConfigurationError('Private key is required');
    }
  }

  public authenticate(): MiddlewareFunction {
    return async (req: any, _res: any, next: (error?: any) => void) => {
      try {
        // Extract agent ID from header
        const agentId = req.headers?.['x-phlow-agent-id'] || req.headers?.['X-Phlow-Agent-Id'];
        if (!agentId) {
          throw new AuthenticationError('Agent ID not provided', 'AGENT_ID_MISSING');
        }

        // Extract JWT token
        const token = this.extractToken(req);
        if (!token) {
          throw new AuthenticationError('No token provided', 'TOKEN_MISSING');
        }

        // Get remote agent's public key
        const remoteAgent = await this.getAgentCard(agentId);
        if (!remoteAgent) {
          throw new AuthenticationError('Agent not found', 'AGENT_NOT_FOUND');
        }

        // Verify JWT signature
        const claims = verifyToken(token, remoteAgent.publicKey, {
          audience: this.config.agentCard.agentId,
          issuer: agentId,
        });

        // Create context for downstream handlers
        const context: PhlowContext = {
          agent: remoteAgent,
          token,
          claims,
          supabase: this.supabase,
        };

        (req as any).phlow = context;
        next();
      } catch (error) {
        next(error);
      }
    };
  }


  private extractToken(req: any): string | null {
    const authHeader = req.headers?.authorization || req.headers?.Authorization;
    if (authHeader && authHeader.startsWith('Bearer ')) {
      return authHeader.substring(7);
    }
    return null;
  }


  private async getAgentCard(agentId: string): Promise<AgentCard | null> {
    try {
      const { data, error } = await this.supabase
        .from('agent_cards')
        .select('*')
        .eq('agent_id', agentId)
        .single();

      if (error || !data) {
        return null;
      }

      // Map from database to A2A-compatible AgentCard format
      return {
        agentId: data.agent_id,
        name: data.name,
        description: data.description,
        publicKey: data.public_key,
        serviceUrl: data.service_url,
        schemaVersion: data.schema_version || '0.1.0',
        skills: data.skills || [],
        securitySchemes: data.security_schemes || {
          'phlow-jwt': {
            type: 'http',
            scheme: 'bearer',
            bearerFormat: 'JWT'
          }
        },
        metadata: data.metadata,
      };
    } catch (error) {
      console.error('Error fetching agent card:', error);
      return null;
    }
  }

  public getSupabaseClient(): SupabaseClient {
    return this.supabase;
  }

  public getCurrentAgentCard() {
    return this.config.agentCard;
  }

  // A2A-compatible well-known endpoint handler
  public wellKnownHandler(): MiddlewareFunction {
    return (_req: any, res: any) => {
      const agentCard = {
        schemaVersion: this.config.agentCard.schemaVersion || '0.1.0',
        name: this.config.agentCard.name,
        description: this.config.agentCard.description,
        serviceUrl: this.config.agentCard.serviceUrl,
        skills: this.config.agentCard.skills || [],
        securitySchemes: this.config.agentCard.securitySchemes || {
          'phlow-jwt': {
            type: 'http',
            scheme: 'bearer',
            bearerFormat: 'JWT'
          }
        },
        metadata: {
          ...this.config.agentCard.metadata,
          publicKey: this.config.agentCard.publicKey,
          agentId: this.config.agentCard.agentId,
        }
      };

      res.setHeader('Content-Type', 'application/json');
      res.json(agentCard);
    };
  }
}