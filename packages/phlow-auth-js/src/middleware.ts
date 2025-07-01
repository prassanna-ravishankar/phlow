import { createClient, SupabaseClient } from '@supabase/supabase-js';
import { PhlowConfig, PhlowContext, VerifyOptions, MiddlewareFunction } from './types';
import { verifyToken, isTokenExpired } from './jwt';
import { AuthenticationError, AuthorizationError, ConfigurationError } from './errors';
import { RateLimiter } from './rate-limiter';
import { AuditLogger } from './audit';

export class PhlowMiddleware {
  private supabase: SupabaseClient;
  private config: PhlowConfig;
  private rateLimiter?: RateLimiter;
  private auditLogger?: AuditLogger;

  constructor(config: PhlowConfig) {
    this.validateConfig(config);
    this.config = config;
    
    this.supabase = createClient(config.supabaseUrl, config.supabaseAnonKey);

    if (config.options?.rateLimiting) {
      this.rateLimiter = new RateLimiter(
        config.options.rateLimiting.maxRequests,
        config.options.rateLimiting.windowMs
      );
    }

    if (config.options?.enableAudit) {
      this.auditLogger = new AuditLogger(this.supabase);
    }
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

  public authenticate(options?: VerifyOptions): MiddlewareFunction {
    return async (req: any, res: any, next: (error?: any) => void) => {
      try {
        const agentId = this.extractAgentId(req);
        
        if (this.rateLimiter && !this.rateLimiter.isAllowed(agentId)) {
          await this.auditLogger?.log({
            timestamp: new Date(),
            event: 'auth_failure',
            agentId,
            details: { reason: 'rate_limit_exceeded' },
          });
          throw new AuthenticationError('Rate limit exceeded', 'RATE_LIMIT');
        }

        const token = this.extractToken(req);
        if (!token) {
          await this.auditLogger?.log({
            timestamp: new Date(),
            event: 'auth_failure',
            agentId: 'unknown',
            details: { reason: 'missing_token' },
          });
          throw new AuthenticationError('No token provided', 'TOKEN_MISSING');
        }

        const remoteAgent = await this.getAgentCard(agentId);
        if (!remoteAgent) {
          await this.auditLogger?.log({
            timestamp: new Date(),
            event: 'auth_failure',
            agentId,
            details: { reason: 'agent_not_found' },
          });
          throw new AuthenticationError('Agent not found', 'AGENT_NOT_FOUND');
        }

        const claims = verifyToken(token, remoteAgent.publicKey, {
          audience: this.config.agentCard.agentId,
          issuer: agentId,
          ignoreExpiration: options?.allowExpired,
        });

        if (options?.requiredPermissions) {
          const hasPermissions = options.requiredPermissions.every(perm =>
            claims.permissions.includes(perm)
          );
          
          if (!hasPermissions) {
            await this.auditLogger?.log({
              timestamp: new Date(),
              event: 'permission_denied',
              agentId,
              targetAgentId: this.config.agentCard.agentId,
              details: { 
                required: options.requiredPermissions,
                provided: claims.permissions,
              },
            });
            throw new AuthorizationError('Insufficient permissions', 'INSUFFICIENT_PERMISSIONS');
          }
        }

        const context: PhlowContext = {
          agent: remoteAgent,
          token,
          claims,
          supabase: this.supabase,
        };

        (req as any).phlow = context;

        await this.auditLogger?.log({
          timestamp: new Date(),
          event: 'auth_success',
          agentId,
          targetAgentId: this.config.agentCard.agentId,
        });

        next();
      } catch (error) {
        next(error);
      }
    };
  }

  public refreshTokenIfNeeded(): MiddlewareFunction {
    return async (req: any, res: any, next: (error?: any) => void) => {
      try {
        const context = (req as any).phlow as PhlowContext;
        if (!context) {
          return next();
        }

        const threshold = this.config.options?.refreshThreshold || 300;
        if (isTokenExpired(context.token, threshold)) {
          await this.auditLogger?.log({
            timestamp: new Date(),
            event: 'token_refresh',
            agentId: context.agent.agentId,
            targetAgentId: this.config.agentCard.agentId,
          });
          
          res.setHeader('X-Phlow-Token-Refresh', 'true');
        }

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

  private extractAgentId(req: any): string {
    const agentId = req.headers?.['x-phlow-agent-id'] || 
                    req.headers?.['X-Phlow-Agent-Id'];
    if (!agentId) {
      throw new AuthenticationError('Agent ID not provided', 'AGENT_ID_MISSING');
    }
    return agentId;
  }

  private async getAgentCard(agentId: string): Promise<any> {
    try {
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
    } catch (error) {
      console.error('Error fetching agent card:', error);
      return null;
    }
  }

  public getSupabaseClient(): SupabaseClient {
    return this.supabase;
  }

  public getAgentCard() {
    return this.config.agentCard;
  }
}