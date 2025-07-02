import { SupabaseClient } from '@supabase/supabase-js';

// A2A-compatible AgentCard format
export interface AgentCard {
  agentId: string;
  name: string;
  description?: string;
  publicKey: string;
  serviceUrl?: string;
  // A2A compatibility fields
  schemaVersion?: string;
  skills?: Array<{
    name: string;
    description?: string;
  }>;
  securitySchemes?: Record<string, any>;
  permissions?: string[];
  endpoints?: Record<string, any>;
  metadata?: Record<string, any>;
}

export interface PhlowConfig {
  supabaseUrl: string;
  supabaseAnonKey: string;
  agentCard: AgentCard;
  privateKey: string;
}

export interface PhlowContext {
  agent: AgentCard;
  token: string;
  claims: JWTClaims;
  supabase: SupabaseClient;
}

export interface JWTClaims {
  sub: string;    // Subject (agent being authenticated)
  iss: string;    // Issuer (agent making the request)
  aud: string;    // Audience (target agent)
  exp: number;    // Expiration timestamp
  iat: number;    // Issued at timestamp
  // A2A-compatible fields
  skills?: string[];
  metadata?: Record<string, any>;
}

export type MiddlewareFunction = (
  req: any,
  res: any,
  next: (error?: any) => void
) => void | Promise<void>;