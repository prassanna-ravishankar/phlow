from phlow_auth import PhlowAuth
import asyncio

# Create a client agent
phlow = PhlowAuth(
    agent_card={
        "name": "ResearchBot",
        "description": "AI agent that conducts research using other agents"
    }
)

# Discover and use another agent's capabilities
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

# Run the analysis
if __name__ == "__main__":
    result = asyncio.run(analyze_data("https://example.com/dataset.csv"))
    print(result)