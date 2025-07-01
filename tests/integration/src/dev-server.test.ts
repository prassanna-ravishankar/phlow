import axios from 'axios';
import { DevServer } from 'phlow-dev';
import { setupTestEnvironment, generateTestToken } from './setup';

describe('Development Server Integration', () => {
  let testEnv: ReturnType<typeof setupTestEnvironment>;
  let devServer: DevServer;
  let serverUrl: string;

  beforeAll(async () => {
    testEnv = setupTestEnvironment();
    
    devServer = new DevServer({
      port: 0, // Use random available port
      enableCors: true,
      enableTestEndpoints: true,
      mockAgents: [
        testEnv.agents.source.agentCard,
        testEnv.agents.target.agentCard,
        testEnv.agents.admin.agentCard,
        testEnv.agents.limited.agentCard,
      ],
    });

    // Initialize mock Supabase
    devServer.initializeMockSupabase();

    // Start server
    const port = await startServerOnRandomPort(devServer);
    serverUrl = `http://localhost:${port}`;
  });

  afterAll(async () => {
    // Clean up server if needed
  });

  describe('Basic Endpoints', () => {
    test('health endpoint should respond', async () => {
      const response = await axios.get(`${serverUrl}/health`);
      
      expect(response.status).toBe(200);
      expect(response.data.status).toBe('ok');
      expect(response.data.timestamp).toBeDefined();
    });

    test('mock agents endpoint should list agents', async () => {
      const response = await axios.get(`${serverUrl}/mock/agents`);
      
      expect(response.status).toBe(200);
      expect(response.data.agents).toBeDefined();
      expect(response.data.agents.length).toBeGreaterThan(0);
      
      const agentIds = response.data.agents.map((agent: any) => agent.agentId);
      expect(agentIds).toContain(testEnv.agents.source.agentCard.agentId);
      expect(agentIds).toContain(testEnv.agents.target.agentCard.agentId);
    });

    test('should add new mock agents', async () => {
      const newAgent = {
        agentId: 'test-new-agent',
        name: 'Test New Agent',
        permissions: ['test:permission'],
        publicKey: testEnv.agents.source.agentCard.publicKey,
      };

      const response = await axios.post(`${serverUrl}/mock/agents`, newAgent);
      
      expect(response.status).toBe(200);
      expect(response.data.success).toBe(true);
      expect(response.data.agent.agentId).toBe(newAgent.agentId);

      // Verify agent was added
      const listResponse = await axios.get(`${serverUrl}/mock/agents`);
      const agentIds = listResponse.data.agents.map((agent: any) => agent.agentId);
      expect(agentIds).toContain(newAgent.agentId);
    });
  });

  describe('Test Scenario Endpoints', () => {
    test('should list available test scenarios', async () => {
      const response = await axios.get(`${serverUrl}/test/scenarios-list`);
      
      expect(response.status).toBe(200);
      expect(response.data.scenarios).toBeDefined();
      expect(response.data.scenarios.length).toBeGreaterThan(0);
      
      const scenarioNames = response.data.scenarios.map((s: any) => s.name);
      expect(scenarioNames).toContain('valid_jwt_authentication');
      expect(scenarioNames).toContain('expired_token_handling');
    });

    test('should run all test scenarios', async () => {
      const response = await axios.get(`${serverUrl}/test/scenarios`);
      
      expect(response.status).toBe(200);
      expect(response.data.summary).toBeDefined();
      expect(response.data.results).toBeDefined();
      
      const { summary, results } = response.data;
      expect(summary.total).toBeGreaterThan(0);
      expect(summary.passed).toBeGreaterThan(0);
      expect(summary.failed).toBe(0); // All tests should pass
      
      // Check individual results
      expect(results['valid_jwt_authentication']).toBeDefined();
      expect(results['valid_jwt_authentication'].success).toBe(true);
    });

    test('should run specific test scenario', async () => {
      const scenarioName = 'valid_jwt_authentication';
      const response = await axios.get(`${serverUrl}/test/scenarios/${scenarioName}`);
      
      expect(response.status).toBe(200);
      expect(response.data.scenario.name).toBe(scenarioName);
      expect(response.data.result.success).toBe(true);
      expect(response.data.result.data).toBeDefined();
    });

    test('should handle unknown test scenario', async () => {
      try {
        await axios.get(`${serverUrl}/test/scenarios/unknown-scenario`);
        fail('Should have thrown an error');
      } catch (error: any) {
        expect(error.response.status).toBe(404);
        expect(error.response.data.error).toContain('Test scenario not found');
        expect(error.response.data.available).toBeDefined();
      }
    });
  });

  describe('Custom Route Integration', () => {
    test('should support adding custom routes', async () => {
      devServer.addCustomRoute('get', '/custom-test', (req, res) => {
        res.json({ message: 'Custom route works!', timestamp: new Date().toISOString() });
      });

      const response = await axios.get(`${serverUrl}/custom-test`);
      
      expect(response.status).toBe(200);
      expect(response.data.message).toBe('Custom route works!');
      expect(response.data.timestamp).toBeDefined();
    });

    test('should support POST routes with data', async () => {
      devServer.addCustomRoute('post', '/custom-post', (req, res) => {
        res.json({ 
          received: req.body,
          echo: `Hello ${req.body.name || 'Anonymous'}!`,
        });
      });

      const testData = { name: 'Test User', action: 'test' };
      const response = await axios.post(`${serverUrl}/custom-post`, testData);
      
      expect(response.status).toBe(200);
      expect(response.data.received).toEqual(testData);
      expect(response.data.echo).toBe('Hello Test User!');
    });
  });

  describe('Error Handling', () => {
    test('should handle invalid endpoints gracefully', async () => {
      try {
        await axios.get(`${serverUrl}/non-existent-endpoint`);
        fail('Should have thrown an error');
      } catch (error: any) {
        expect(error.response.status).toBe(404);
      }
    });

    test('should handle malformed requests', async () => {
      try {
        await axios.post(`${serverUrl}/mock/agents`, 'invalid-json', {
          headers: { 'Content-Type': 'application/json' },
        });
        fail('Should have thrown an error');
      } catch (error: any) {
        expect(error.response.status).toBeGreaterThanOrEqual(400);
      }
    });
  });
});

// Helper function to start server on random port
async function startServerOnRandomPort(server: DevServer): Promise<number> {
  return new Promise((resolve, reject) => {
    const app = server.getExpressApp();
    const serverInstance = app.listen(0, () => {
      const address = serverInstance.address();
      if (address && typeof address === 'object') {
        resolve(address.port);
      } else {
        reject(new Error('Failed to get server port'));
      }
    });
  });
}