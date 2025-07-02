# Agent Cards: Self-Describing AI Agents

Agent Cards are the heart of the A2A Protocol, transforming AI agents into self-describing, discoverable services. With Phlow, implementing Agent Cards is remarkably simple.

## The Power of Agent Cards

Imagine a world where AI agents can:
- Automatically discover each other's capabilities
- Understand how to interact without manual integration
- Authenticate and communicate securely
- Form intelligent networks that self-organize

This is the reality Agent Cards enable.

## Quick Implementation

### 1. Create a Specialized Agent

Define your agent's capabilities once, and it becomes discoverable by the entire A2A ecosystem.

**JavaScript**
```javascript
import { phlowAuth } from 'phlow-auth';

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
```

**Python**
```python
from phlow_auth import PhlowAuth
from flask import Flask, request, jsonify

app = Flask(__name__)

phlow = PhlowAuth(
    agent_card={
        "name": "DataWizard",
        "description": "AI agent specialized in data analysis and visualization",
        "skills": ["data-analysis", "visualization", "statistical-modeling"],
        "endpoints": {
            "analyze": {"method": "POST", "path": "/analyze"},
            "visualize": {"method": "POST", "path": "/visualize"}
        }
    }
)

@app.route('/analyze', methods=['POST'])
@phlow.authenticate()
def analyze():
    data = request.json
    # Perform analysis...
    return jsonify({
        "results": "Analysis complete",
        "requestedBy": request.agent['name']
    })

@app.route('/.well-known/agent.json')
def agent_card():
    return phlow.well_known_handler()
```

### 2. Discover and Use Other Agents

Any agent can discover and interact with your agent programmatically.

**JavaScript**
```javascript
import { phlowAuth } from 'phlow-auth';

const researchAgent = phlowAuth({
  agentCard: {
    name: "ResearchBot",
    description: "AI agent that conducts research using other agents"
  }
});

async function analyzeData(datasetUrl) {
  // Discover agent capabilities
  const agentCard = await researchAgent.discoverAgent('https://data-wizard.ai');
  console.log(`Found agent: ${agentCard.name}`);
  console.log(`Skills: ${agentCard.skills.join(', ')}`);
  
  // Authenticate and make request
  const response = await researchAgent.callAgent('https://data-wizard.ai/analyze', {
    dataset: datasetUrl,
    analysis_type: 'regression'
  });
  
  return response.results;
}
```

**Python**
```python
from phlow_auth import PhlowAuth
import asyncio

phlow = PhlowAuth(
    agent_card={
        "name": "ResearchBot",
        "description": "AI agent that conducts research using other agents"
    }
)

async def analyze_data(dataset_url):
    # Discover agent capabilities
    agent_card = await phlow.discover_agent('https://data-wizard.ai')
    print(f"Found agent: {agent_card['name']}")
    print(f"Skills: {', '.join(agent_card['skills'])}")
    
    # Authenticate and make request
    response = await phlow.call_agent(
        'https://data-wizard.ai/analyze',
        json={
            'dataset': dataset_url,
            'analysis_type': 'regression'
        }
    )
    
    return response['results']
```

## What Just Happened?

With minimal code, you've created agents that can:

1. **Self-Describe** - The agent card at `/.well-known/agent.json` tells other agents everything they need to know
2. **Authenticate** - JWT-based authentication happens automatically between agents
3. **Discover** - Agents can find each other's capabilities programmatically
4. **Collaborate** - Secure communication with automatic authentication

## Real-World Applications

### Multi-Agent Research Network
```javascript
// Research coordinator discovers specialized agents
const analysisAgent = await coordinator.discoverAgent('analysis.ai');
const dataAgent = await coordinator.discoverAgent('data-collector.ai');
const reportAgent = await coordinator.discoverAgent('report-writer.ai');

// Orchestrate complex workflows
const data = await coordinator.callAgent('data-collector.ai/collect', { topic });
const analysis = await coordinator.callAgent('analysis.ai/analyze', { data });
const report = await coordinator.callAgent('report-writer.ai/generate', { analysis });
```

### Agent Marketplace
```javascript
// Agents advertise their capabilities
const agents = await marketplace.searchAgents({ 
  skills: ['translation', 'summarization'] 
});

// Dynamic agent selection based on capabilities
const bestAgent = agents.find(a => 
  a.skills.includes('medical-translation') && 
  a.metadata.accuracy > 0.95
);
```

## Agent Card Specification

Phlow implements the full A2A Protocol AgentCard specification:

```typescript
interface AgentCard {
  // Core identification
  agentId: string;
  name: string;
  description: string;
  
  // Authentication
  publicKey: string;
  serviceUrl: string;
  
  // Capabilities
  skills: Array<{
    name: string;
    description: string;
  }>;
  
  // API specification
  endpoints: Record<string, {
    method: string;
    path: string;
    description?: string;
  }>;
  
  // Security
  securitySchemes: {
    bearer?: { type: 'bearer', scheme: 'bearer' };
    apiKey?: { type: 'apiKey', in: 'header', name: string };
  };
  
  // Permissions and metadata
  permissions: string[];
  metadata: Record<string, any>;
}
```

## Best Practices

1. **Clear Skill Definitions** - Use standardized skill names when possible
2. **Comprehensive Descriptions** - Help other agents understand your capabilities
3. **Endpoint Documentation** - Include descriptions for complex endpoints
4. **Version Your API** - Use metadata to indicate API versions
5. **Security First** - Always use authentication for sensitive operations

## Advanced Features

### Skill-Based Discovery
```javascript
// Find agents with specific capabilities
const agents = await phlow.searchAgents({
  skills: ['data-analysis', 'visualization'],
  minTrustScore: 0.8
});
```

### Dynamic Agent Networks
```javascript
// Agents can form networks based on complementary skills
const network = await phlow.createNetwork({
  goal: 'comprehensive-market-analysis',
  requiredSkills: ['data-collection', 'analysis', 'visualization', 'reporting']
});
```

### Agent Reputation
```javascript
// Track and use agent reputation
const agent = await phlow.discoverAgent('https://agent.ai');
if (agent.metadata.reputation?.score > 0.9) {
  // Use highly-rated agent
}
```

## Try It Yourself

Check out the complete examples:
- [Basic Agent Card Setup](../examples/agent-card-showcase/)
- [Multi-Agent Network](../examples/multi-agent-network/)
- [A2A Compatible Agent](../examples/a2a-compatible-agent/)

Every agent becomes part of a self-organizing, intelligent network. That's the magic of Agent Cards with Phlow.