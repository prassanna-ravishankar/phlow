import { AgentCard, generateToken, verifyToken } from 'phlow-auth';

export interface TestScenario {
  name: string;
  description: string;
  setup: () => Promise<TestContext>;
  execute: (context: TestContext) => Promise<TestResult>;
  cleanup?: (context: TestContext) => Promise<void>;
}

export interface TestContext {
  sourceAgent: AgentCard;
  targetAgent: AgentCard;
  sourcePrivateKey: string;
  targetPrivateKey: string;
  token?: string;
  [key: string]: any;
}

export interface TestResult {
  success: boolean;
  message: string;
  data?: any;
  error?: string;
}

export const TEST_SCENARIOS: TestScenario[] = [
  {
    name: 'valid_jwt_authentication',
    description: 'Test successful JWT authentication between agents',
    setup: async () => {
      const { generateKeyPair } = await import('node-forge');
      const forge = await import('node-forge');

      const sourceKeys = forge.pki.rsa.generateKeyPair(2048);
      const targetKeys = forge.pki.rsa.generateKeyPair(2048);

      const sourceAgent: AgentCard = {
        agentId: 'test-source-agent',
        name: 'Test Source Agent',
        permissions: ['read:data', 'write:data'],
        publicKey: forge.pki.publicKeyToPem(sourceKeys.publicKey),
      };

      const targetAgent: AgentCard = {
        agentId: 'test-target-agent',
        name: 'Test Target Agent',
        permissions: ['read:data'],
        publicKey: forge.pki.publicKeyToPem(targetKeys.publicKey),
      };

      return {
        sourceAgent,
        targetAgent,
        sourcePrivateKey: forge.pki.privateKeyToPem(sourceKeys.privateKey),
        targetPrivateKey: forge.pki.privateKeyToPem(targetKeys.privateKey),
      };
    },
    execute: async (context) => {
      try {
        const token = generateToken(
          context.sourceAgent,
          context.sourcePrivateKey,
          context.targetAgent.agentId
        );

        const claims = verifyToken(token, context.sourceAgent.publicKey, {
          audience: context.targetAgent.agentId,
          issuer: context.sourceAgent.agentId,
        });

        return {
          success: true,
          message: 'JWT authentication successful',
          data: { claims, token },
        };
      } catch (error: any) {
        return {
          success: false,
          message: 'JWT authentication failed',
          error: error.message,
        };
      }
    },
  },

  {
    name: 'expired_token_handling',
    description: 'Test handling of expired tokens',
    setup: async () => {
      const forge = await import('node-forge');
      const keys = forge.pki.rsa.generateKeyPair(2048);

      const agent: AgentCard = {
        agentId: 'test-expiry-agent',
        name: 'Test Expiry Agent',
        permissions: ['read:data'],
        publicKey: forge.pki.publicKeyToPem(keys.publicKey),
      };

      return {
        sourceAgent: agent,
        targetAgent: agent,
        sourcePrivateKey: forge.pki.privateKeyToPem(keys.privateKey),
        targetPrivateKey: forge.pki.privateKeyToPem(keys.privateKey),
      };
    },
    execute: async (context) => {
      try {
        // Generate an already expired token (1 second expiry, then wait)
        const token = generateToken(
          context.sourceAgent,
          context.sourcePrivateKey,
          context.targetAgent.agentId,
          '1s'
        );

        // Wait for token to expire
        await new Promise(resolve => setTimeout(resolve, 1100));

        try {
          verifyToken(token, context.sourceAgent.publicKey);
          return {
            success: false,
            message: 'Token should have been rejected as expired',
          };
        } catch (error: any) {
          if (error.code === 'TOKEN_EXPIRED') {
            return {
              success: true,
              message: 'Expired token correctly rejected',
              data: { error: error.message },
            };
          }
          throw error;
        }
      } catch (error: any) {
        return {
          success: false,
          message: 'Unexpected error in expired token test',
          error: error.message,
        };
      }
    },
  },

  {
    name: 'invalid_signature_rejection',
    description: 'Test rejection of tokens with invalid signatures',
    setup: async () => {
      const forge = await import('node-forge');
      const keys1 = forge.pki.rsa.generateKeyPair(2048);
      const keys2 = forge.pki.rsa.generateKeyPair(2048);

      const sourceAgent: AgentCard = {
        agentId: 'test-source-agent',
        name: 'Test Source Agent',
        permissions: ['read:data'],
        publicKey: forge.pki.publicKeyToPem(keys1.publicKey),
      };

      const targetAgent: AgentCard = {
        agentId: 'test-target-agent',
        name: 'Test Target Agent',
        permissions: ['read:data'],
        publicKey: forge.pki.publicKeyToPem(keys2.publicKey),
      };

      return {
        sourceAgent,
        targetAgent,
        sourcePrivateKey: forge.pki.privateKeyToPem(keys1.privateKey),
        targetPrivateKey: forge.pki.privateKeyToPem(keys2.privateKey),
      };
    },
    execute: async (context) => {
      try {
        // Generate token with source agent's key
        const token = generateToken(
          context.sourceAgent,
          context.sourcePrivateKey,
          context.targetAgent.agentId
        );

        try {
          // Try to verify with target agent's key (should fail)
          verifyToken(token, context.targetAgent.publicKey);
          return {
            success: false,
            message: 'Token should have been rejected due to invalid signature',
          };
        } catch (error: any) {
          if (error.code === 'TOKEN_INVALID') {
            return {
              success: true,
              message: 'Invalid signature correctly rejected',
              data: { error: error.message },
            };
          }
          throw error;
        }
      } catch (error: any) {
        return {
          success: false,
          message: 'Unexpected error in signature validation test',
          error: error.message,
        };
      }
    },
  },

  {
    name: 'permission_validation',
    description: 'Test permission-based access control',
    setup: async () => {
      const forge = await import('node-forge');
      const keys = forge.pki.rsa.generateKeyPair(2048);

      const limitedAgent: AgentCard = {
        agentId: 'test-limited-agent',
        name: 'Test Limited Agent',
        permissions: ['read:data'], // Only read permission
        publicKey: forge.pki.publicKeyToPem(keys.publicKey),
      };

      return {
        sourceAgent: limitedAgent,
        targetAgent: limitedAgent,
        sourcePrivateKey: forge.pki.privateKeyToPem(keys.privateKey),
        targetPrivateKey: forge.pki.privateKeyToPem(keys.privateKey),
      };
    },
    execute: async (context) => {
      try {
        const token = generateToken(
          context.sourceAgent,
          context.sourcePrivateKey,
          context.targetAgent.agentId
        );

        const claims = verifyToken(token, context.sourceAgent.publicKey);

        // Check if agent has write permission (should not)
        const hasWritePermission = claims.permissions.includes('write:data');
        const hasReadPermission = claims.permissions.includes('read:data');

        return {
          success: hasReadPermission && !hasWritePermission,
          message: hasReadPermission && !hasWritePermission
            ? 'Permission validation successful'
            : 'Permission validation failed',
          data: {
            permissions: claims.permissions,
            hasRead: hasReadPermission,
            hasWrite: hasWritePermission,
          },
        };
      } catch (error: any) {
        return {
          success: false,
          message: 'Permission validation test failed',
          error: error.message,
        };
      }
    },
  },
];

export class TestRunner {
  async runScenario(scenario: TestScenario): Promise<TestResult> {
    let context: TestContext | undefined;
    
    try {
      context = await scenario.setup();
      const result = await scenario.execute(context);
      
      if (scenario.cleanup && context) {
        await scenario.cleanup(context);
      }
      
      return result;
    } catch (error: any) {
      return {
        success: false,
        message: `Test scenario failed: ${error.message}`,
        error: error.message,
      };
    }
  }

  async runAllScenarios(): Promise<Map<string, TestResult>> {
    const results = new Map<string, TestResult>();
    
    for (const scenario of TEST_SCENARIOS) {
      const result = await this.runScenario(scenario);
      results.set(scenario.name, result);
    }
    
    return results;
  }
}