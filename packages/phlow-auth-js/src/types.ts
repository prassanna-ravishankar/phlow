import { SupabaseClient } from '@supabase/supabase-js';
import { AgentCard as A2AAgentCard } from '@a2a-js/sdk';

export interface PhlowConfig {
  // Supabase configuration
  supabaseUrl: string;
  supabaseAnonKey: string;
  
  // Agent configuration (A2A-compliant)
  agentCard: A2AAgentCard;
  privateKey: string;
  
  // Phlow-specific options
  enableAuditLog?: boolean;
  enableRateLimiting?: boolean;
  rateLimitConfig?: RateLimitConfig;
}

export interface PhlowContext {
  // From A2A authentication
  agent: A2AAgentCard;
  token: string;
  claims: any;
  
  // Phlow additions
  supabase: SupabaseClient;
}

export interface RateLimitConfig {
  windowMs: number;
  maxRequests: number;
  keyGenerator?: (req: any) => string;
}

export type MiddlewareFunction = (
  req: any,
  res: any,
  next: (error?: any) => void
) => void | Promise<void>;

// Supabase-specific types
export interface SupabaseAgentRecord {
  agent_id: string;
  name: string;
  description?: string;
  service_url?: string;
  schema_version: string;
  skills: any[];
  security_schemes: Record<string, any>;
  public_key: string;
  metadata?: Record<string, any>;
  created_at: string;
  updated_at?: string;
}

export interface AuthAuditLog {
  id?: string;
  agent_id: string;
  timestamp: string;
  event_type: 'authentication' | 'authorization' | 'rate_limit';
  success: boolean;
  metadata?: Record<string, any>;
  error_code?: string;
  error_message?: string;
}