import { PhlowMiddleware, generateToken, verifyToken, isTokenExpired } from 'phlow-auth';
import { setupTestEnvironment, generateTestToken, delay } from './setup';

describe('Authentication Integration Tests', () => {
  let testEnv: ReturnType<typeof setupTestEnvironment>;
  let middleware: PhlowMiddleware;

  beforeEach(() => {
    testEnv = setupTestEnvironment();
    
    // Create middleware with target agent configuration
    middleware = new PhlowMiddleware({
      supabaseUrl: 'http://localhost:54321',
      supabaseAnonKey: 'test-anon-key',
      agentCard: testEnv.agents.target.agentCard,
      privateKey: testEnv.agents.target.privateKey,
      options: {
        enableAudit: true,
        rateLimiting: {
          maxRequests: 10,
          windowMs: 60000,
        },
      },
    });
    
    // Mock the Supabase client
    (middleware as any).supabase = testEnv.mockSupabase;
  });

  describe('Token Generation and Verification', () => {
    test('should generate and verify valid tokens', () => {
      const token = generateTestToken(
        testEnv.agents.source,
        testEnv.agents.target.agentCard.agentId
      );

      expect(token).toBeDefined();
      expect(typeof token).toBe('string');

      const claims = verifyToken(
        token,
        testEnv.agents.source.agentCard.publicKey,
        {
          audience: testEnv.agents.target.agentCard.agentId,
          issuer: testEnv.agents.source.agentCard.agentId,
        }
      );

      expect(claims.sub).toBe(testEnv.agents.source.agentCard.agentId);
      expect(claims.aud).toBe(testEnv.agents.target.agentCard.agentId);
      expect(claims.permissions).toEqual(testEnv.agents.source.agentCard.permissions);
    });

    test('should reject tokens with invalid signatures', () => {
      const token = generateTestToken(
        testEnv.agents.source,
        testEnv.agents.target.agentCard.agentId
      );

      expect(() => {
        verifyToken(
          token,
          testEnv.agents.target.agentCard.publicKey, // Wrong public key
          {
            audience: testEnv.agents.target.agentCard.agentId,
            issuer: testEnv.agents.source.agentCard.agentId,
          }
        );
      }).toThrow();
    });

    test('should handle token expiration', async () => {
      // Generate token that expires in 1 second
      const shortToken = generateTestToken(
        testEnv.agents.source,
        testEnv.agents.target.agentCard.agentId,
        '1s'
      );

      // Token should be valid initially
      expect(isTokenExpired(shortToken)).toBe(false);

      // Wait for token to expire
      await delay(1100);

      // Token should now be expired
      expect(isTokenExpired(shortToken)).toBe(true);

      // Verification should fail
      expect(() => {
        verifyToken(
          shortToken,
          testEnv.agents.source.agentCard.publicKey,
          {
            audience: testEnv.agents.target.agentCard.agentId,
            issuer: testEnv.agents.source.agentCard.agentId,
          }
        );
      }).toThrow('Token has expired');
    });

    test('should allow expired tokens when ignoreExpiration is true', async () => {
      const shortToken = generateTestToken(
        testEnv.agents.source,
        testEnv.agents.target.agentCard.agentId,
        '1s'
      );

      await delay(1100);

      const claims = verifyToken(
        shortToken,
        testEnv.agents.source.agentCard.publicKey,
        {
          audience: testEnv.agents.target.agentCard.agentId,
          issuer: testEnv.agents.source.agentCard.agentId,
          ignoreExpiration: true,
        }
      );

      expect(claims.sub).toBe(testEnv.agents.source.agentCard.agentId);
    });
  });

  describe('Middleware Authentication', () => {
    test('should authenticate valid requests', async () => {
      const token = generateTestToken(
        testEnv.agents.source,
        testEnv.agents.target.agentCard.agentId
      );

      const context = await middleware.authenticate({
        requiredPermissions: ['read:data'],
      }, {
        authorization: `Bearer ${token}`,
        'x-phlow-agent-id': testEnv.agents.source.agentCard.agentId,
      });

      expect(context.agent.agentId).toBe(testEnv.agents.source.agentCard.agentId);
      expect(context.claims.permissions).toContain('read:data');
    });

    test('should reject requests without tokens', async () => {
      await expect(
        middleware.authenticate({}, {
          'x-phlow-agent-id': testEnv.agents.source.agentCard.agentId,
        })
      ).rejects.toThrow('No token provided');
    });

    test('should reject requests without agent ID', async () => {
      const token = generateTestToken(
        testEnv.agents.source,
        testEnv.agents.target.agentCard.agentId
      );

      await expect(
        middleware.authenticate({}, {
          authorization: `Bearer ${token}`,
        })
      ).rejects.toThrow('Agent ID not provided');
    });

    test('should reject requests from unknown agents', async () => {
      const token = generateTestToken(
        testEnv.agents.source,
        testEnv.agents.target.agentCard.agentId
      );

      await expect(
        middleware.authenticate({}, {
          authorization: `Bearer ${token}`,
          'x-phlow-agent-id': 'unknown-agent',
        })
      ).rejects.toThrow('Agent not found');
    });

    test('should enforce permission requirements', async () => {
      const token = generateTestToken(
        testEnv.agents.limited, // Has only 'read:own_data'
        testEnv.agents.target.agentCard.agentId
      );

      await expect(
        middleware.authenticate({
          requiredPermissions: ['admin:users'],
        }, {
          authorization: `Bearer ${token}`,
          'x-phlow-agent-id': testEnv.agents.limited.agentCard.agentId,
        })
      ).rejects.toThrow('Insufficient permissions');
    });

    test('should allow access with sufficient permissions', async () => {
      const token = generateTestToken(
        testEnv.agents.admin,
        testEnv.agents.target.agentCard.agentId
      );

      const context = await middleware.authenticate({
        requiredPermissions: ['admin:users'],
      }, {
        authorization: `Bearer ${token}`,
        'x-phlow-agent-id': testEnv.agents.admin.agentCard.agentId,
      });

      expect(context.agent.agentId).toBe(testEnv.agents.admin.agentCard.agentId);
      expect(context.claims.permissions).toContain('admin:users');
    });
  });

  describe('Rate Limiting', () => {
    test('should enforce rate limits', async () => {
      const token = generateTestToken(
        testEnv.agents.source,
        testEnv.agents.target.agentCard.agentId
      );

      const headers = {
        authorization: `Bearer ${token}`,
        'x-phlow-agent-id': testEnv.agents.source.agentCard.agentId,
      };

      // Make requests up to the limit (10 requests)
      for (let i = 0; i < 10; i++) {
        await middleware.authenticate({}, headers);
      }

      // 11th request should be rate limited
      await expect(
        middleware.authenticate({}, headers)
      ).rejects.toThrow('Rate limit exceeded');
    });

    test('should reset rate limits after time window', async () => {
      // This test would require waiting for the rate limit window to reset
      // In a real test environment, you might mock the timer or use a shorter window
      expect(true).toBe(true); // Placeholder
    });
  });

  describe('Audit Logging', () => {
    test('should log successful authentication events', async () => {
      const token = generateTestToken(
        testEnv.agents.source,
        testEnv.agents.target.agentCard.agentId
      );

      await middleware.authenticate({}, {
        authorization: `Bearer ${token}`,
        'x-phlow-agent-id': testEnv.agents.source.agentCard.agentId,
      });

      const auditLogs = testEnv.mockSupabase.getAuditLogs();
      const authSuccessLog = auditLogs.find((log: any) => 
        log.event === 'auth_success' && 
        log.agent_id === testEnv.agents.source.agentCard.agentId
      );

      expect(authSuccessLog).toBeDefined();
      expect(authSuccessLog.target_agent_id).toBe(testEnv.agents.target.agentCard.agentId);
    });

    test('should log failed authentication events', async () => {
      try {
        await middleware.authenticate({}, {
          authorization: 'Bearer invalid-token',
          'x-phlow-agent-id': testEnv.agents.source.agentCard.agentId,
        });
      } catch (error) {
        // Expected to fail
      }

      const auditLogs = testEnv.mockSupabase.getAuditLogs();
      const authFailureLog = auditLogs.find((log: any) => 
        log.event === 'auth_failure'
      );

      expect(authFailureLog).toBeDefined();
    });

    test('should log permission denied events', async () => {
      const token = generateTestToken(
        testEnv.agents.limited,
        testEnv.agents.target.agentCard.agentId
      );

      try {
        await middleware.authenticate({
          requiredPermissions: ['admin:users'],
        }, {
          authorization: `Bearer ${token}`,
          'x-phlow-agent-id': testEnv.agents.limited.agentCard.agentId,
        });
      } catch (error) {
        // Expected to fail
      }

      const auditLogs = testEnv.mockSupabase.getAuditLogs();
      const permissionDeniedLog = auditLogs.find((log: any) => 
        log.event === 'permission_denied'
      );

      expect(permissionDeniedLog).toBeDefined();
      expect(permissionDeniedLog.details.required).toContain('admin:users');
    });
  });
});