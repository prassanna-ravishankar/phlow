import { SupabaseClient } from '@supabase/supabase-js';
import { JwtPayload } from 'jsonwebtoken';

// A2A-compliant AgentCard interface
export interface AgentCard {
  schemaVersion: string;
  name: string;
  description: string;
  serviceUrl: string;
  skills: string[];
  securitySchemes: Record<string, unknown>;
  metadata?: {
    agentId?: string;
    publicKey?: string;
    [key: string]: unknown;
  };
}

export interface PhlowConfig {
  // Supabase configuration
  supabaseUrl: string;
  supabaseAnonKey: string;
  
  // Agent configuration (A2A-compliant)
  agentCard: AgentCard;
  privateKey: string;
  publicKey?: string;
  
  // Phlow-specific options
  enableAuditLog?: boolean;
  enableRateLimiting?: boolean;
  rateLimitConfig?: RateLimitConfig;
}

export interface PhlowContext {
  // From A2A authentication
  agent: AgentCard;
  token: string;
  claims: JwtPayload;
  
  // Phlow additions
  supabase: SupabaseClient;
  a2aClient?: unknown; // A2AClient when available
  a2aServer?: unknown; // A2AServer when available
}

export interface RateLimitConfig {
  windowMs: number;
  maxRequests: number;
  keyGenerator?: (req: unknown) => string;
}

export type MiddlewareFunction = (
  req: unknown,
  res: unknown,
  next: (error?: unknown) => void
) => void | Promise<void>;

// Supabase-specific types
export interface SupabaseAgentRecord {
  agent_id: string;
  name: string;
  description?: string;
  service_url?: string;
  schema_version: string;
  skills: string[];
  security_schemes: Record<string, unknown>;
  public_key: string;
  metadata?: Record<string, unknown>;
  created_at: string;
  updated_at?: string;
}

export interface AuthAuditLog {
  id?: string;
  agent_id: string;
  timestamp: string;
  event_type: 'authentication' | 'authorization' | 'rate_limit';
  success: boolean;
  metadata?: Record<string, unknown>;
  error_code?: string;
  error_message?: string;
}