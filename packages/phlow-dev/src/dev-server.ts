import express from 'express';
import cors from 'cors';
import { PhlowMiddleware, AgentCard } from 'phlow-auth';
import { MockSupabase } from './mock-supabase';
import { TestRunner, TEST_SCENARIOS } from './test-scenarios';

export interface DevServerConfig {
  port?: number;
  enableCors?: boolean;
  mockAgents?: AgentCard[];
  enableTestEndpoints?: boolean;
}

export class DevServer {
  private app: express.Application;
  private mockSupabase?: MockSupabase;
  private testRunner: TestRunner;

  constructor(private config: DevServerConfig = {}) {
    this.app = express();
    this.testRunner = new TestRunner();
    this.setupMiddleware();
    this.setupRoutes();
  }

  private setupMiddleware(): void {
    if (this.config.enableCors) {
      this.app.use(cors());
    }
    
    this.app.use(express.json());
    
    // Request logging
    this.app.use((req, _res, next) => {
      console.log(`${new Date().toISOString()} ${req.method} ${req.path}`);
      next();
    });
  }

  private setupRoutes(): void {
    // Health check
    this.app.get('/health', (_req, res) => {
      res.json({
        status: 'ok',
        timestamp: new Date().toISOString(),
        version: '0.1.0',
      });
    });

    // Mock Supabase info
    this.app.get('/mock/agents', (_req, res) => {
      if (!this.mockSupabase) {
        return res.status(404).json({ error: 'Mock Supabase not initialized' });
      }
      
      return res.json({
        agents: this.mockSupabase.getAllAgents(),
      });
    });

    this.app.post('/mock/agents', (req, res) => {
      if (!this.mockSupabase) {
        return res.status(404).json({ error: 'Mock Supabase not initialized' });
      }
      
      const agent = req.body as AgentCard;
      this.mockSupabase.addAgent(agent);
      
      return res.json({ success: true, agent });
    });

    // Test endpoints
    if (this.config.enableTestEndpoints) {
      this.setupTestEndpoints();
    }
  }

  private setupTestEndpoints(): void {
    // Run all test scenarios
    this.app.get('/test/scenarios', async (_req, res) => {
      try {
        const results = await this.testRunner.runAllScenarios();
        const summary = {
          total: results.size,
          passed: Array.from(results.values()).filter(r => r.success).length,
          failed: Array.from(results.values()).filter(r => !r.success).length,
        };
        
        return res.json({
          summary,
          results: Object.fromEntries(results),
        });
      } catch (error: any) {
        return res.status(500).json({
          error: 'Failed to run test scenarios',
          message: error.message,
        });
      }
    });

    // Run specific test scenario
    this.app.get('/test/scenarios/:name', async (req, res) => {
      const scenarioName = req.params.name;
      const scenario = TEST_SCENARIOS.find(s => s.name === scenarioName);
      
      if (!scenario) {
        return res.status(404).json({
          error: 'Test scenario not found',
          available: TEST_SCENARIOS.map(s => s.name),
        });
      }

      try {
        const result = await this.testRunner.runScenario(scenario);
        return res.json({
          scenario: {
            name: scenario.name,
            description: scenario.description,
          },
          result,
        });
      } catch (error: any) {
        return res.status(500).json({
          error: 'Failed to run test scenario',
          message: error.message,
        });
      }
    });

    // List available test scenarios
    this.app.get('/test/scenarios-list', (_req, res) => {
      return res.json({
        scenarios: TEST_SCENARIOS.map(s => ({
          name: s.name,
          description: s.description,
        })),
      });
    });
  }

  initializeMockSupabase(agents: AgentCard[] = []): MockSupabase {
    this.mockSupabase = new MockSupabase({
      agents: [...(this.config.mockAgents || []), ...agents],
      enableAuditLogs: true,
    });
    
    return this.mockSupabase;
  }

  addPhlowMiddleware(middleware: PhlowMiddleware, path: string = '/protected'): void {
    this.app.get(path, middleware.authenticate(), (req: any, res) => {
      return res.json({
        message: 'Access granted!',
        agent: req.phlow.agent,
        claims: req.phlow.claims,
        timestamp: new Date().toISOString(),
      });
    });
  }

  addCustomRoute(
    method: 'get' | 'post' | 'put' | 'delete',
    path: string,
    handler: express.RequestHandler
  ): void {
    this.app[method](path, handler);
  }

  async start(port?: number): Promise<void> {
    const serverPort = port || this.config.port || 3000;
    
    return new Promise((resolve) => {
      this.app.listen(serverPort, () => {
        console.log(`🚀 Dev server running on http://localhost:${serverPort}`);
        console.log(`📊 Health check: http://localhost:${serverPort}/health`);
        
        if (this.mockSupabase) {
          console.log(`🗃️  Mock agents: http://localhost:${serverPort}/mock/agents`);
        }
        
        if (this.config.enableTestEndpoints) {
          console.log(`🧪 Test scenarios: http://localhost:${serverPort}/test/scenarios`);
        }
        
        resolve();
      });
    });
  }

  getExpressApp(): express.Application {
    return this.app;
  }
}