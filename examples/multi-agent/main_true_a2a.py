"""
True Multi-Agent A2A Communication Example

Demonstrates agents autonomously discovering and communicating with each other.
Agents make their own decisions about when to delegate tasks to other agents.
"""

import os
import threading
import time
import uuid

import requests
import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI

from phlow import AgentCard, generate_token

# Load environment variables
load_dotenv()

# Global registry of known agents (in production, use Supabase)
AGENT_REGISTRY = {}
AGENT_PRIVATE_KEY = os.environ.get("PHLOW_PRIVATE_KEY", "test-secret-key")


def create_intelligent_agent(
    agent_id: str,
    agent_name: str,
    agent_description: str,
    capabilities: list,
    port: int,
):
    """Create an intelligent A2A-compliant agent that can discover and call other agents"""
    app = FastAPI(title=f"Phlow Agent: {agent_name}")

    # Store agent's own info
    agent_info = {
        "id": agent_id,
        "name": agent_name,
        "description": agent_description,
        "capabilities": capabilities,
        "port": port,
        "url": f"http://127.0.0.1:{port}",
    }

    # A2A Agent Card (discovery endpoint)
    @app.get("/.well-known/agent.json")
    def agent_card():
        return {
            "id": agent_id,
            "name": agent_name,
            "description": agent_description,
            "version": "1.0.0",
            "author": "Phlow Framework",
            "capabilities": {cap: True for cap in capabilities},
            "input_modes": ["text"],
            "output_modes": ["text"],
            "endpoints": {"task": "/tasks/send"},
            "metadata": {
                "framework": "phlow",
                "model": "gemini-2.5-flash-lite",
                "specialization": capabilities[0] if capabilities else "general",
                "port": port,
            },
        }

    def discover_agents_with_capability(capability: str) -> list[dict]:
        """Discover agents with a specific capability from the registry"""
        matching_agents = []
        for agent_id, agent_data in AGENT_REGISTRY.items():
            if agent_id != agent_info["id"]:  # Don't discover self
                if capability in agent_data.get("capabilities", []):
                    matching_agents.append(agent_data)
        return matching_agents

    def call_agent(agent_url: str, message: str) -> dict | None:
        """Call another agent with authentication"""
        try:
            # Create agent card for auth
            my_agent_card = AgentCard(
                agent_id=agent_info["id"],
                name=agent_info["name"],
                description=agent_info["description"],
                permissions=agent_info["capabilities"],
                public_key="dummy-key",  # In production, use real key
            )

            # Generate auth token
            token = generate_token(my_agent_card, AGENT_PRIVATE_KEY)

            # Prepare task
            task_payload = {
                "id": str(uuid.uuid4()),
                "message": {
                    "role": "user",
                    "parts": [{"type": "text", "text": message}],
                },
                "metadata": {"from_agent": agent_info["id"], "delegated": True},
            }

            # Make authenticated request
            headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
                "User-Agent": f"Phlow/{agent_info['name']}",
            }

            response = requests.post(
                f"{agent_url}/tasks/send",
                json=task_payload,
                headers=headers,
                timeout=15,
            )

            if response.status_code == 200:
                return response.json()
            else:
                print(f"❌ Agent returned {response.status_code}: {response.text}")

        except Exception as e:
            print(f"❌ Failed to call agent at {agent_url}: {e}")

        return None

    def extract_response_text(response: dict) -> str:
        """Extract text from A2A response"""
        text = ""
        for msg in response.get("messages", []):
            if msg.get("role") == "agent":
                for part in msg.get("parts", []):
                    if part.get("type") == "text":
                        text += part.get("text", "")
        return text

    # A2A Task endpoint with intelligent routing
    @app.post("/tasks/send")
    async def send_task(task: dict):
        try:
            task_id = task.get("id", str(uuid.uuid4()))
            message = task.get("message", {})
            metadata = task.get("metadata", {})
            user_text = ""

            if "parts" in message:
                for part in message["parts"]:
                    if part.get("type") == "text":
                        user_text += part.get("text", "")
            else:
                user_text = message.get("text", "Hello")

            print(f"\n🤖 {agent_name} received: '{user_text}'")
            print(f"   From: {metadata.get('from_agent', 'external client')}")

            # INTELLIGENT ROUTING LOGIC
            response_text = ""

            # DataAnalyst Agent Logic
            if agent_id == "data-analyst-001":
                # Analyze the data
                if os.environ.get("GEMINI_API_KEY"):
                    try:
                        from google import genai

                        client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
                        prompt = f"You are {agent_name}. Analyze this data/request and provide insights: {user_text}"
                        response = client.models.generate_content(
                            model="gemini-2.5-flash-lite", contents=prompt
                        )
                        response_text = response.text
                    except Exception:
                        response_text = "Analysis: The data shows a 25% increase, indicating strong growth momentum."
                else:
                    response_text = "Analysis: The data shows a 25% increase, indicating strong growth momentum."

                # Check if content creation is needed
                if "marketing" in user_text.lower() or "content" in user_text.lower():
                    print("   🔄 Delegating to ContentWriter for marketing content...")
                    writers = discover_agents_with_capability("content_writing")
                    if writers:
                        writer_response = call_agent(
                            writers[0]["url"],
                            f"Create marketing content based on this analysis: {response_text}",
                        )
                        if writer_response:
                            writer_text = extract_response_text(writer_response)
                            response_text += (
                                f"\n\n[ContentWriter's Marketing Plan]: {writer_text}"
                            )

            # ContentWriter Agent Logic
            elif agent_id == "content-writer-001":
                # Check if we need data analysis first
                if "analyze" in user_text.lower() and "delegated" not in metadata:
                    print(
                        "   🔄 Need data analysis first, delegating to DataAnalyst..."
                    )
                    analysts = discover_agents_with_capability("data_analysis")
                    if analysts:
                        analyst_response = call_agent(
                            analysts[0]["url"],
                            f"Please analyze this for content creation: {user_text}",
                        )
                        if analyst_response:
                            analysis = extract_response_text(analyst_response)
                            user_text = (
                                f"Based on this analysis: {analysis}, {user_text}"
                            )

                # Create content
                if os.environ.get("GEMINI_API_KEY"):
                    try:
                        from google import genai

                        client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
                        prompt = f"You are {agent_name}. Create compelling marketing content: {user_text}"
                        response = client.models.generate_content(
                            model="gemini-2.5-flash-lite", contents=prompt
                        )
                        response_text = response.text
                    except Exception:
                        response_text = "Marketing Campaign: 'Accelerate Your Success - 25% Growth Achieved!'"
                else:
                    response_text = "Marketing Campaign: 'Accelerate Your Success - 25% Growth Achieved!'"

            # CodeReviewer Agent Logic
            elif agent_id == "code-reviewer-001":
                # Review code or delegate if needed
                if "statistics" in user_text.lower() or "data" in user_text.lower():
                    print(
                        "   🔄 This needs data analysis, delegating to DataAnalyst..."
                    )
                    analysts = discover_agents_with_capability("data_analysis")
                    if analysts:
                        analyst_response = call_agent(analysts[0]["url"], user_text)
                        if analyst_response:
                            response_text = f"DataAnalyst provided: {extract_response_text(analyst_response)}"
                else:
                    response_text = (
                        "Code review complete. The implementation looks solid."
                    )

            print(f"   ✅ Responding with: {response_text[:100]}...")

            return {
                "id": task_id,
                "status": {
                    "state": "completed",
                    "message": "Task completed successfully",
                },
                "messages": [
                    {
                        "role": "agent",
                        "parts": [{"type": "text", "text": response_text}],
                    }
                ],
                "artifacts": [],
                "metadata": {
                    "agent_id": agent_id,
                    "model": "gemini-2.5-flash-lite",
                    "framework": "phlow",
                    "specialization": capabilities[0] if capabilities else "general",
                },
            }

        except Exception as e:
            return {
                "id": task.get("id", "unknown"),
                "status": {"state": "failed", "message": f"Task failed: {str(e)}"},
                "messages": [
                    {
                        "role": "agent",
                        "parts": [{"type": "text", "text": f"Error: {str(e)}"}],
                    }
                ],
                "artifacts": [],
                "metadata": {"agent_id": agent_id, "error": str(e)},
            }

    # Health endpoint
    @app.get("/health")
    def health():
        return {"status": "healthy", "agent_id": agent_id}

    return app, agent_info


def start_agent_server(app: FastAPI, port: int):
    """Start agent server in background thread"""

    def run_server():
        uvicorn.run(app, host="127.0.0.1", port=port, log_level="error")

    thread = threading.Thread(target=run_server, daemon=True)
    thread.start()
    return thread


def main():
    """Main true multi-agent demonstration"""
    print("🚀 Starting TRUE Multi-Agent A2A Communication Demo...")
    print("   Agents will autonomously discover and communicate with each other!\n")

    # Define specialized agents
    agents_config = [
        {
            "id": "data-analyst-001",
            "name": "DataAnalyst Agent",
            "description": "Specializes in data analysis and insights",
            "capabilities": ["data_analysis", "statistics", "visualization"],
            "port": 8001,
        },
        {
            "id": "content-writer-001",
            "name": "ContentWriter Agent",
            "description": "Specializes in content creation and writing",
            "capabilities": ["content_writing", "editing", "marketing"],
            "port": 8002,
        },
        {
            "id": "code-reviewer-001",
            "name": "CodeReviewer Agent",
            "description": "Specializes in code review and software engineering",
            "capabilities": ["code_review", "software_engineering", "debugging"],
            "port": 8003,
        },
    ]

    # Start all agents and register them
    print(f"🤖 Starting {len(agents_config)} specialized agents...")
    for agent_config in agents_config:
        app, agent_info = create_intelligent_agent(
            agent_config["id"],
            agent_config["name"],
            agent_config["description"],
            agent_config["capabilities"],
            agent_config["port"],
        )
        start_agent_server(app, agent_config["port"])

        # Register agent in the registry
        AGENT_REGISTRY[agent_config["id"]] = {
            "id": agent_config["id"],
            "name": agent_config["name"],
            "description": agent_config["description"],
            "capabilities": agent_config["capabilities"],
            "url": f"http://127.0.0.1:{agent_config['port']}",
        }

        print(f"   ✅ {agent_config['name']}: http://127.0.0.1:{agent_config['port']}")

    # Wait for agents to start
    time.sleep(3)

    # Demonstrate TRUE agent-to-agent communication
    print("\n💬 Demonstrating TRUE A2A communication...")
    print("   Watch how agents autonomously delegate tasks to each other!\n")

    # Example 1: Ask ContentWriter to create marketing material (it will consult DataAnalyst)
    print(
        "📝 Example 1: Asking ContentWriter to create data-driven marketing content..."
    )
    print("   (ContentWriter will autonomously consult DataAnalyst)\n")

    task_payload = {
        "id": str(uuid.uuid4()),
        "message": {
            "role": "user",
            "parts": [
                {
                    "type": "text",
                    "text": "Create marketing content for our Q4 results showing 25% sales growth. I need both analysis and compelling copy.",
                }
            ],
        },
    }

    response = requests.post(
        "http://127.0.0.1:8002/tasks/send",  # ContentWriter
        json=task_payload,
        timeout=30,
    )

    if response.status_code == 200:
        result = response.json()
        response_text = ""
        for msg in result.get("messages", []):
            if msg.get("role") == "agent":
                for part in msg.get("parts", []):
                    if part.get("type") == "text":
                        response_text += part.get("text", "")
        print(f"\n📄 ContentWriter's Response:\n{response_text}\n")

    time.sleep(2)

    # Example 2: Ask DataAnalyst for marketing insights (it will engage ContentWriter)
    print(
        "\n📊 Example 2: Asking DataAnalyst for analysis with marketing recommendations..."
    )
    print("   (DataAnalyst will autonomously engage ContentWriter)\n")

    task_payload = {
        "id": str(uuid.uuid4()),
        "message": {
            "role": "user",
            "parts": [
                {
                    "type": "text",
                    "text": "Analyze our 25% quarterly growth and suggest marketing strategies.",
                }
            ],
        },
    }

    response = requests.post(
        "http://127.0.0.1:8001/tasks/send",  # DataAnalyst
        json=task_payload,
        timeout=30,
    )

    if response.status_code == 200:
        result = response.json()
        response_text = ""
        for msg in result.get("messages", []):
            if msg.get("role") == "agent":
                for part in msg.get("parts", []):
                    if part.get("type") == "text":
                        response_text += part.get("text", "")
        print(f"\n📄 DataAnalyst's Response:\n{response_text}\n")

    print("\n🌐 Agent endpoints:")
    for _agent_id, agent_data in AGENT_REGISTRY.items():
        print(f"   {agent_data['name']}:")
        print(f"     Agent Card: {agent_data['url']}/.well-known/agent.json")
        print(f"     Task Endpoint: {agent_data['url']}/tasks/send")
        print(f"     Capabilities: {', '.join(agent_data['capabilities'])}")

    print("\n⏰ Agents will run indefinitely. Press Ctrl+C to stop.")
    print("💡 Try sending your own requests to see agents collaborate!\n")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n👋 Shutting down multi-agent demo...")


if __name__ == "__main__":
    main()
