# Agent Cards: Self-Describing AI Agents

Agent Cards transform AI agents into self-describing, discoverable services. Any agent can learn what another agent can do and how to interact with it - automatically.

## The Power in Action

### 1. Create a Specialized Agent

**JavaScript**
```javascript
const dataAnalysisAgent = phlowAuth({
  agentCard: {
    name: "DataWizard",
    description: "AI agent specialized in data analysis and visualization",
    skills: ["data-analysis", "visualization", "statistical-modeling"],
    endpoints: {
      analyze: { method: "POST", path: "/analyze" },
      visualize: { method: "POST", "path": "/visualize" }
    }
  }
});

// That's it! Your agent now:
// ✓ Describes its capabilities at /.well-known/agent.json
// ✓ Authenticates incoming agent requests
// ✓ Is discoverable by other agents
```

**Python**
```python
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
```

### 2. Discover and Use Other Agents

**JavaScript**
```javascript
// Discover what an agent can do
const agentCard = await researchAgent.discoverAgent('https://data-wizard.ai');
console.log(`Skills: ${agentCard.skills.join(', ')}`);

// Use it - authentication handled automatically
const response = await researchAgent.callAgent('https://data-wizard.ai/analyze', {
  dataset: datasetUrl,
  analysis_type: 'regression'
});
```

**Python**
```python
# Discover what an agent can do
agent_card = await phlow.discover_agent('https://data-wizard.ai')
print(f"Skills: {', '.join(agent_card['skills'])}")

# Use it - authentication handled automatically
response = await phlow.call_agent(
    'https://data-wizard.ai/analyze',
    json={'dataset': dataset_url, 'analysis_type': 'regression'}
)
```

## What Just Happened?

With just a few lines of code, you've created agents that can:

1. **Self-Describe** - Other agents instantly know their capabilities
2. **Authenticate** - Secure agent-to-agent communication out of the box
3. **Discover** - Find and understand other agents programmatically
4. **Collaborate** - Call other agents' endpoints with automatic auth

No manual API documentation. No authentication boilerplate. No discovery protocols. 

Just agents that understand each other.

## Real-World Impact

Imagine a network where:
- A research agent finds data analysis agents by their skills
- A writing agent discovers fact-checking agents automatically
- A code generation agent uses testing agents to verify its output
- All without hardcoded integrations or manual configuration

This is the power of Agent Cards with Phlow.

## Try It Yourself

Check out the full examples:
- `data-analysis-agent.js` / `.py` - A complete specialized agent
- `client-agent.js` / `.py` - An agent that discovers and uses others

Every agent becomes part of a self-organizing, intelligent network. That's the magic of Agent Cards.