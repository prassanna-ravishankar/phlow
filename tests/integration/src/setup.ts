import { createMockSupabase } from 'phlow-dev';
import { AgentCard, generateToken } from 'phlow-auth';
import forge from 'node-forge';

export interface TestAgent {
  agentCard: AgentCard;
  publicKey: string;
  privateKey: string;
}

export interface TestEnvironment {
  agents: {
    source: TestAgent;
    target: TestAgent;
    admin: TestAgent;
    limited: TestAgent;
  };
  mockSupabase: any;
}

export function generateTestKeyPair(): { publicKey: string; privateKey: string } {
  const keypair = forge.pki.rsa.generateKeyPair(2048);
  return {
    publicKey: forge.pki.publicKeyToPem(keypair.publicKey),
    privateKey: forge.pki.privateKeyToPem(keypair.privateKey),
  };
}

export function createTestAgent(
  agentId: string,
  name: string,
  permissions: string[] = ['read:data']
): TestAgent {
  const { publicKey, privateKey } = generateTestKeyPair();
  
  const agentCard: AgentCard = {
    agentId,
    name,
    description: `Test agent: ${name}`,
    permissions,
    publicKey,
    endpoints: {
      api: `http://localhost:3000`,
    },
    metadata: {
      environment: 'test',
      created: new Date().toISOString(),
    },
  };

  return {
    agentCard,
    publicKey,
    privateKey,
  };
}

export function setupTestEnvironment(): TestEnvironment {
  // Create test agents
  const sourceAgent = createTestAgent('source-agent', 'Source Test Agent', [
    'read:data',
    'write:data',
    'send:messages',
  ]);

  const targetAgent = createTestAgent('target-agent', 'Target Test Agent', [
    'read:data',
    'write:data',
    'receive:messages',
  ]);

  const adminAgent = createTestAgent('admin-agent', 'Admin Test Agent', [
    'read:data',
    'write:data',
    'admin:users',
    'admin:agents',
    'audit:logs',
  ]);

  const limitedAgent = createTestAgent('limited-agent', 'Limited Test Agent', [
    'read:own_data',
  ]);

  // Create mock Supabase with test agents
  const mockSupabase = createMockSupabase({
    agents: [
      sourceAgent.agentCard,
      targetAgent.agentCard,
      adminAgent.agentCard,
      limitedAgent.agentCard,
    ],
    enableAuditLogs: true,
  });

  return {
    agents: {
      source: sourceAgent,
      target: targetAgent,
      admin: adminAgent,
      limited: limitedAgent,
    },
    mockSupabase,
  };
}

export function generateTestToken(
  sourceAgent: TestAgent,
  targetAgentId: string,
  expiresIn: string = '1h'
): string {
  return generateToken(
    sourceAgent.agentCard,
    sourceAgent.privateKey,
    targetAgentId,
    expiresIn
  );
}

export function delay(ms: number): Promise<void> {
  return new Promise(resolve => setTimeout(resolve, ms));
}