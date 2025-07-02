import { phlowAuth } from 'phlow-auth';

// Create a client agent
const researchAgent = phlowAuth({
  agentCard: {
    name: "ResearchBot",
    description: "AI agent that conducts research using other agents"
  }
});

// Discover and use another agent's capabilities
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