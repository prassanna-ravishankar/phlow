// Phlow: A2A Protocol Extension with Supabase Integration
export { PhlowMiddleware } from './middleware';

// Supabase helpers
export { SupabaseHelpers } from './supabase-helpers';

// Errors
export { PhlowError, AuthenticationError, ConfigurationError } from './errors';

// Types
export * from './types';

// Re-export useful A2A types for convenience
export type { 
  AgentCard as A2AAgentCard,
  A2AContext,
  A2AServer,
  A2AClient,
  Task,
  Message
} from '@a2a-js/sdk';