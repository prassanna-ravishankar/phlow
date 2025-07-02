import { phlowAuth } from 'phlow-auth';

// Define your agent's capabilities with an Agent Card
const dataAnalysisAgent = phlowAuth({
  agentCard: {
    name: "DataWizard",
    description: "AI agent specialized in data analysis and visualization",
    skills: ["data-analysis", "visualization", "statistical-modeling"],
    endpoints: {
      analyze: { method: "POST", path: "/analyze" },
      visualize: { method: "POST", path: "/visualize" }
    }
  }
});

// Your agent's endpoints - protected automatically
app.post('/analyze', dataAnalysisAgent.authenticate(), async (req, res) => {
  const { dataset, analysis_type } = req.body;
  // Perform analysis...
  res.json({ results: "Analysis complete", requestedBy: req.agent.name });
});

// Agent card automatically exposed at /.well-known/agent.json
app.get('/.well-known/agent.json', dataAnalysisAgent.wellKnownHandler());