import axios from 'axios';
import { PhlowMiddleware, SupabaseHelpers } from 'phlow-auth';
import { createMockSupabase } from 'phlow-dev';
import { setupTestEnvironment, generateTestToken } from './setup';

describe('End-to-End Integration Tests', () => {
  let testEnv: ReturnType<typeof setupTestEnvironment>;
  let sourceMiddleware: PhlowMiddleware;
  let targetMiddleware: PhlowMiddleware;
  let supabaseHelpers: SupabaseHelpers;

  beforeEach(() => {
    testEnv = setupTestEnvironment();

    // Create middleware for source agent
    sourceMiddleware = new PhlowMiddleware({
      supabaseUrl: 'http://localhost:54321',
      supabaseAnonKey: 'test-anon-key',
      agentCard: testEnv.agents.source.agentCard,
      privateKey: testEnv.agents.source.privateKey,
      options: {
        enableAudit: true,
        rateLimiting: {
          maxRequests: 100,
          windowMs: 60000,
        },
      },
    });

    // Create middleware for target agent
    targetMiddleware = new PhlowMiddleware({
      supabaseUrl: 'http://localhost:54321',
      supabaseAnonKey: 'test-anon-key',
      agentCard: testEnv.agents.target.agentCard,
      privateKey: testEnv.agents.target.privateKey,
      options: {
        enableAudit: true,
      },
    });

    // Mock Supabase clients
    (sourceMiddleware as any).supabase = testEnv.mockSupabase;
    (targetMiddleware as any).supabase = testEnv.mockSupabase;

    // Create Supabase helpers
    supabaseHelpers = new SupabaseHelpers(testEnv.mockSupabase);
  });

  describe('Complete Agent-to-Agent Flow', () => {
    test('should complete full authentication flow between agents', async () => {
      // Step 1: Source agent generates token for target agent
      const token = generateTestToken(
        testEnv.agents.source,
        testEnv.agents.target.agentCard.agentId
      );

      expect(token).toBeDefined();

      // Step 2: Target agent receives and authenticates the request
      const context = await targetMiddleware.authenticate({
        requiredPermissions: ['read:data'],
      }, {
        authorization: `Bearer ${token}`,
        'x-phlow-agent-id': testEnv.agents.source.agentCard.agentId,
      });

      expect(context.agent.agentId).toBe(testEnv.agents.source.agentCard.agentId);
      expect(context.claims.permissions).toContain('read:data');

      // Step 3: Verify audit logs were created
      const auditLogs = testEnv.mockSupabase.getAuditLogs();
      const authSuccessLog = auditLogs.find((log: any) => 
        log.event === 'auth_success' && 
        log.agent_id === testEnv.agents.source.agentCard.agentId
      );

      expect(authSuccessLog).toBeDefined();
    });

    test('should handle bidirectional communication', async () => {
      // Source -> Target
      const sourceToTargetToken = generateTestToken(
        testEnv.agents.source,
        testEnv.agents.target.agentCard.agentId
      );

      const sourceToTargetContext = await targetMiddleware.authenticate({}, {
        authorization: `Bearer ${sourceToTargetToken}`,
        'x-phlow-agent-id': testEnv.agents.source.agentCard.agentId,
      });

      expect(sourceToTargetContext.agent.agentId).toBe(testEnv.agents.source.agentCard.agentId);

      // Target -> Source (reverse communication)
      const targetToSourceToken = generateTestToken(
        testEnv.agents.target,
        testEnv.agents.source.agentCard.agentId
      );

      const targetToSourceContext = await sourceMiddleware.authenticate({}, {
        authorization: `Bearer ${targetToSourceToken}`,
        'x-phlow-agent-id': testEnv.agents.target.agentCard.agentId,
      });

      expect(targetToSourceContext.agent.agentId).toBe(testEnv.agents.target.agentCard.agentId);
    });

    test('should enforce permission boundaries across agents', async () => {
      // Admin agent accessing target agent with admin permissions
      const adminToken = generateTestToken(
        testEnv.agents.admin,
        testEnv.agents.target.agentCard.agentId
      );

      const adminContext = await targetMiddleware.authenticate({
        requiredPermissions: ['admin:users'],
      }, {
        authorization: `Bearer ${adminToken}`,
        'x-phlow-agent-id': testEnv.agents.admin.agentCard.agentId,
      });

      expect(adminContext.agent.agentId).toBe(testEnv.agents.admin.agentCard.agentId);

      // Limited agent should fail to access admin endpoints
      const limitedToken = generateTestToken(
        testEnv.agents.limited,
        testEnv.agents.target.agentCard.agentId
      );

      await expect(
        targetMiddleware.authenticate({
          requiredPermissions: ['admin:users'],
        }, {
          authorization: `Bearer ${limitedToken}`,
          'x-phlow-agent-id': testEnv.agents.limited.agentCard.agentId,
        })
      ).rejects.toThrow('Insufficient permissions');
    });
  });

  describe('Supabase Integration', () => {
    test('should register and retrieve agent cards', async () => {
      const newAgent = {
        agentId: 'e2e-test-agent',
        name: 'E2E Test Agent',
        description: 'Agent created during E2E testing',
        permissions: ['e2e:test', 'read:data'],
        publicKey: testEnv.agents.source.agentCard.publicKey,
        metadata: {
          testRun: new Date().toISOString(),
          environment: 'e2e-test',
        },
      };

      // Register agent
      await supabaseHelpers.registerAgentCard(newAgent);

      // Retrieve agent
      const retrievedAgent = await supabaseHelpers.getAgentCard(newAgent.agentId);

      expect(retrievedAgent).toBeDefined();
      expect(retrievedAgent!.agentId).toBe(newAgent.agentId);
      expect(retrievedAgent!.name).toBe(newAgent.name);
      expect(retrievedAgent!.permissions).toEqual(newAgent.permissions);
    });

    test('should list agents with filters', async () => {
      // List agents with specific permission
      const readAgents = await supabaseHelpers.listAgentCards(['read:data']);
      
      expect(readAgents.length).toBeGreaterThan(0);
      readAgents.forEach(agent => {
        expect(agent.permissions).toContain('read:data');
      });

      // List agents with metadata filter
      const testAgents = await supabaseHelpers.listAgentCards(
        undefined,
        { environment: 'test' }
      );

      expect(testAgents.length).toBeGreaterThan(0);
      testAgents.forEach(agent => {
        expect(agent.metadata?.environment).toBe('test');
      });
    });

    test('should handle agent card updates', async () => {
      const originalAgent = testEnv.agents.source.agentCard;
      
      // Update agent card
      const updatedAgent = {
        ...originalAgent,
        description: 'Updated description for E2E testing',
        permissions: [...originalAgent.permissions, 'new:permission'],
        metadata: {
          ...originalAgent.metadata,
          lastUpdated: new Date().toISOString(),
        },
      };

      await supabaseHelpers.registerAgentCard(updatedAgent);

      // Retrieve updated agent
      const retrievedAgent = await supabaseHelpers.getAgentCard(originalAgent.agentId);

      expect(retrievedAgent).toBeDefined();
      expect(retrievedAgent!.description).toBe(updatedAgent.description);
      expect(retrievedAgent!.permissions).toContain('new:permission');
      expect(retrievedAgent!.metadata?.lastUpdated).toBeDefined();
    });
  });

  describe('Multi-Agent Workflows', () => {
    test('should handle complex multi-step workflow', async () => {
      // Simulate a workflow: Admin -> Target -> Source
      
      // Step 1: Admin initiates workflow
      const adminToken = generateTestToken(
        testEnv.agents.admin,
        testEnv.agents.target.agentCard.agentId
      );

      const adminContext = await targetMiddleware.authenticate({
        requiredPermissions: ['admin:users'],
      }, {
        authorization: `Bearer ${adminToken}`,
        'x-phlow-agent-id': testEnv.agents.admin.agentCard.agentId,
      });

      expect(adminContext.agent.agentId).toBe(testEnv.agents.admin.agentCard.agentId);

      // Step 2: Target processes request and forwards to Source
      const targetToken = generateTestToken(
        testEnv.agents.target,
        testEnv.agents.source.agentCard.agentId
      );

      const targetContext = await sourceMiddleware.authenticate({
        requiredPermissions: ['write:data'],
      }, {
        authorization: `Bearer ${targetToken}`,
        'x-phlow-agent-id': testEnv.agents.target.agentCard.agentId,
      });

      expect(targetContext.agent.agentId).toBe(testEnv.agents.target.agentCard.agentId);

      // Verify audit trail shows the complete workflow
      const auditLogs = testEnv.mockSupabase.getAuditLogs();
      
      const adminAuth = auditLogs.find((log: any) => 
        log.event === 'auth_success' && 
        log.agent_id === testEnv.agents.admin.agentCard.agentId
      );
      
      const targetAuth = auditLogs.find((log: any) => 
        log.event === 'auth_success' && 
        log.agent_id === testEnv.agents.target.agentCard.agentId
      );

      expect(adminAuth).toBeDefined();
      expect(targetAuth).toBeDefined();
    });

    test('should handle workflow failure scenarios', async () => {
      // Attempt workflow with insufficient permissions
      const limitedToken = generateTestToken(
        testEnv.agents.limited,
        testEnv.agents.target.agentCard.agentId
      );

      // Should fail at the target middleware
      await expect(
        targetMiddleware.authenticate({
          requiredPermissions: ['admin:users'],
        }, {
          authorization: `Bearer ${limitedToken}`,
          'x-phlow-agent-id': testEnv.agents.limited.agentCard.agentId,
        })
      ).rejects.toThrow('Insufficient permissions');

      // Verify failure was logged
      const auditLogs = testEnv.mockSupabase.getAuditLogs();
      const permissionDenied = auditLogs.find((log: any) => 
        log.event === 'permission_denied' && 
        log.agent_id === testEnv.agents.limited.agentCard.agentId
      );

      expect(permissionDenied).toBeDefined();
    });
  });

  describe('Performance and Load', () => {
    test('should handle multiple concurrent authentications', async () => {
      const concurrentRequests = 10;
      const token = generateTestToken(
        testEnv.agents.source,
        testEnv.agents.target.agentCard.agentId
      );

      const authPromises = Array.from({ length: concurrentRequests }, (_, i) =>
        targetMiddleware.authenticate({}, {
          authorization: `Bearer ${token}`,
          'x-phlow-agent-id': testEnv.agents.source.agentCard.agentId,
        })
      );

      const results = await Promise.all(authPromises);

      expect(results).toHaveLength(concurrentRequests);
      results.forEach(context => {
        expect(context.agent.agentId).toBe(testEnv.agents.source.agentCard.agentId);
      });
    });

    test('should maintain performance under load', async () => {
      const iterations = 50;
      const startTime = Date.now();

      for (let i = 0; i < iterations; i++) {
        const token = generateTestToken(
          testEnv.agents.source,
          testEnv.agents.target.agentCard.agentId
        );

        await targetMiddleware.authenticate({}, {
          authorization: `Bearer ${token}`,
          'x-phlow-agent-id': testEnv.agents.source.agentCard.agentId,
        });
      }

      const endTime = Date.now();
      const totalTime = endTime - startTime;
      const averageTime = totalTime / iterations;

      // Each authentication should complete in under 100ms on average
      expect(averageTime).toBeLessThan(100);
    });
  });
});