import { SupabaseClient } from '@supabase/supabase-js';

export interface AgentCard {
  agentId: string;
  name: string;
  description?: string;
  permissions: string[];
  publicKey: string;
  endpoints?: {
    auth?: string;
    api?: string;
  };
  metadata?: Record<string, any>;
}

export interface PhlowConfig {
  supabaseUrl: string;
  supabaseAnonKey: string;
  agentCard: AgentCard;
  privateKey: string;
  options?: {
    tokenExpiry?: string;
    refreshThreshold?: number;
    enableAudit?: boolean;
    rateLimiting?: {
      maxRequests: number;
      windowMs: number;
    };
  };
}

export interface PhlowContext {
  agent: AgentCard;
  token: string;
  claims: JWTClaims;
  supabase: SupabaseClient;
}

export interface JWTClaims {
  sub: string;
  iss: string;
  aud: string;
  exp: number;
  iat: number;
  permissions: string[];
  metadata?: Record<string, any>;
}

export interface VerifyOptions {
  requiredPermissions?: string[];
  allowExpired?: boolean;
}

export interface AuditLog {
  timestamp: Date;
  event: 'auth_success' | 'auth_failure' | 'token_refresh' | 'permission_denied';
  agentId: string;
  targetAgentId?: string;
  details?: Record<string, any>;
}

export type MiddlewareFunction = (
  req: any,
  res: any,
  next: (error?: any) => void
) => void | Promise<void>;

export interface TokenPair {
  accessToken: string;
  refreshToken?: string;
}