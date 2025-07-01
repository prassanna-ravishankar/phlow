import { TestRunner, TEST_SCENARIOS } from 'phlow-dev';

describe('Test Scenarios Integration', () => {
  let testRunner: TestRunner;

  beforeEach(() => {
    testRunner = new TestRunner();
  });

  describe('Individual Scenarios', () => {
    test('valid JWT authentication scenario', async () => {
      const scenario = TEST_SCENARIOS.find(s => s.name === 'valid_jwt_authentication');
      expect(scenario).toBeDefined();

      const result = await testRunner.runScenario(scenario!);
      
      expect(result.success).toBe(true);
      expect(result.message).toContain('JWT authentication successful');
      expect(result.data).toBeDefined();
      expect(result.data.claims).toBeDefined();
      expect(result.data.token).toBeDefined();
    });

    test('expired token handling scenario', async () => {
      const scenario = TEST_SCENARIOS.find(s => s.name === 'expired_token_handling');
      expect(scenario).toBeDefined();

      const result = await testRunner.runScenario(scenario!);
      
      expect(result.success).toBe(true);
      expect(result.message).toContain('Expired token correctly rejected');
      expect(result.data?.error).toContain('expired');
    });

    test('invalid signature rejection scenario', async () => {
      const scenario = TEST_SCENARIOS.find(s => s.name === 'invalid_signature_rejection');
      expect(scenario).toBeDefined();

      const result = await testRunner.runScenario(scenario!);
      
      expect(result.success).toBe(true);
      expect(result.message).toContain('Invalid signature correctly rejected');
    });

    test('permission validation scenario', async () => {
      const scenario = TEST_SCENARIOS.find(s => s.name === 'permission_validation');
      expect(scenario).toBeDefined();

      const result = await testRunner.runScenario(scenario!);
      
      expect(result.success).toBe(true);
      expect(result.message).toContain('Permission validation successful');
      expect(result.data?.hasRead).toBe(true);
      expect(result.data?.hasWrite).toBe(false);
    });
  });

  describe('All Scenarios', () => {
    test('should run all scenarios successfully', async () => {
      const results = await testRunner.runAllScenarios();
      
      expect(results.size).toBe(TEST_SCENARIOS.length);
      
      // Check that all scenarios passed
      const failedScenarios: string[] = [];
      results.forEach((result, scenarioName) => {
        if (!result.success) {
          failedScenarios.push(`${scenarioName}: ${result.message}`);
        }
      });

      if (failedScenarios.length > 0) {
        console.error('Failed scenarios:', failedScenarios);
      }

      expect(failedScenarios).toHaveLength(0);
    });

    test('should have consistent scenario results', async () => {
      // Run scenarios multiple times to ensure consistency
      const runs = 3;
      const allResults: Map<string, boolean>[] = [];

      for (let i = 0; i < runs; i++) {
        const results = await testRunner.runAllScenarios();
        const successMap = new Map<string, boolean>();
        
        results.forEach((result, scenarioName) => {
          successMap.set(scenarioName, result.success);
        });
        
        allResults.push(successMap);
      }

      // Compare results across runs
      const firstRun = allResults[0];
      for (let i = 1; i < runs; i++) {
        const currentRun = allResults[i];
        
        firstRun.forEach((success, scenarioName) => {
          expect(currentRun.get(scenarioName)).toBe(success);
        });
      }
    });
  });

  describe('Scenario Error Handling', () => {
    test('should handle scenario setup failures gracefully', async () => {
      const invalidScenario = {
        name: 'invalid_scenario',
        description: 'A scenario that will fail during setup',
        setup: async () => {
          throw new Error('Setup failed');
        },
        execute: async () => {
          return { success: true, message: 'Should not reach here' };
        },
      };

      const result = await testRunner.runScenario(invalidScenario);
      
      expect(result.success).toBe(false);
      expect(result.message).toContain('Test scenario failed');
      expect(result.error).toContain('Setup failed');
    });

    test('should handle scenario execution failures gracefully', async () => {
      const invalidScenario = {
        name: 'failing_execution_scenario',
        description: 'A scenario that fails during execution',
        setup: async () => ({
          sourceAgent: {} as any,
          targetAgent: {} as any,
          sourcePrivateKey: '',
          targetPrivateKey: '',
        }),
        execute: async () => {
          throw new Error('Execution failed');
        },
      };

      const result = await testRunner.runScenario(invalidScenario);
      
      expect(result.success).toBe(false);
      expect(result.message).toContain('Test scenario failed');
      expect(result.error).toContain('Execution failed');
    });
  });

  describe('Scenario Performance', () => {
    test('scenarios should complete within reasonable time', async () => {
      const startTime = Date.now();
      const results = await testRunner.runAllScenarios();
      const endTime = Date.now();
      
      const totalTime = endTime - startTime;
      
      // All scenarios should complete within 30 seconds
      expect(totalTime).toBeLessThan(30000);
      
      // Each scenario should complete within 10 seconds on average
      const averageTime = totalTime / results.size;
      expect(averageTime).toBeLessThan(10000);
    });

    test('individual scenarios should be fast', async () => {
      for (const scenario of TEST_SCENARIOS) {
        const startTime = Date.now();
        await testRunner.runScenario(scenario);
        const endTime = Date.now();
        
        const duration = endTime - startTime;
        
        // Each scenario should complete within 5 seconds
        expect(duration).toBeLessThan(5000);
      }
    });
  });
});