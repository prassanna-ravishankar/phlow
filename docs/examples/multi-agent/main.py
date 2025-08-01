"""
Multi-Agent A2A Communication Example

Demonstrates multiple specialized A2A agents discovering and communicating
with each other. Based on the working test_e2e_multi_agent.py structure.
"""

import os
import time
import uuid
import threading
import socket
import requests
from fastapi import FastAPI
import uvicorn
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def create_agent(agent_id: str, agent_name: str, agent_description: str, capabilities: list, port: int):
    """Create a specialized A2A-compliant agent"""
    app = FastAPI(title=f"Phlow Agent: {agent_name}")
    
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
            "endpoints": {
                "task": "/tasks/send"
            },
            "metadata": {
                "framework": "phlow",
                "model": "gemini-2.5-flash",
                "specialization": capabilities[0] if capabilities else "general",
                "port": port
            }
        }
    
    # A2A Task endpoint
    @app.post("/tasks/send")
    def send_task(task: dict):
        try:
            task_id = task.get("id", str(uuid.uuid4()))
            message = task.get("message", {})
            user_text = ""
            
            if "parts" in message:
                for part in message["parts"]:
                    if part.get("type") == "text":
                        user_text += part.get("text", "")
            else:
                user_text = message.get("text", "Hello")
            
            print(f"🤖 {agent_name} processing: '{user_text}'")
            
            # Use Gemini with agent-specific prompt
            if os.environ.get("GEMINI_API_KEY"):
                try:
                    import google.generativeai as genai
                    genai.configure(api_key=os.environ["GEMINI_API_KEY"])
                    
                    model = genai.GenerativeModel('gemini-2.5-flash')
                    prompt = f"You are {agent_name}, a specialized Phlow A2A agent. {agent_description}. Respond briefly to: {user_text}"
                    response = model.generate_content(prompt)
                    response_text = response.text
                except Exception as e:
                    response_text = f"I'm {agent_name}. I specialize in {', '.join(capabilities)}. You said: {user_text} (Gemini error: {e})"
            else:
                # Fallback response without Gemini
                response_text = f"Hello! I'm {agent_name}. I specialize in {', '.join(capabilities)}. You said: {user_text}"
            
            return {
                "id": task_id,
                "status": {
                    "state": "completed",
                    "message": "Task completed successfully"
                },
                "messages": [
                    {
                        "role": "agent",
                        "parts": [
                            {
                                "type": "text", 
                                "text": response_text
                            }
                        ]
                    }
                ],
                "artifacts": [],
                "metadata": {
                    "agent_id": agent_id,
                    "model": "gemini-2.5-flash",
                    "framework": "phlow",
                    "specialization": capabilities[0] if capabilities else "general"
                }
            }
            
        except Exception as e:
            return {
                "id": task.get("id", "unknown"),
                "status": {
                    "state": "failed",
                    "message": f"Task failed: {str(e)}"
                },
                "messages": [
                    {
                        "role": "agent", 
                        "parts": [
                            {
                                "type": "text",
                                "text": f"Error: {str(e)}"
                            }
                        ]
                    }
                ],
                "artifacts": [],
                "metadata": {
                    "agent_id": agent_id,
                    "error": str(e)
                }
            }
    
    # Health endpoint
    @app.get("/health")
    def health():
        return {"status": "healthy", "agent_id": agent_id}
        
    return app

def discover_agent(agent_url: str):
    """Discover agent using A2A protocol"""
    try:
        response = requests.get(f"{agent_url}/.well-known/agent.json", timeout=5)
        if response.status_code == 200:
            return response.json()
    except Exception as e:
        print(f"❌ Failed to discover agent at {agent_url}: {e}")
    return None

def send_a2a_task(agent_url: str, message_text: str):
    """Send A2A task to agent"""
    task_payload = {
        "id": str(uuid.uuid4()),
        "message": {
            "role": "user",
            "parts": [
                {
                    "type": "text",
                    "text": message_text
                }
            ]
        }
    }
    
    try:
        response = requests.post(
            f"{agent_url}/tasks/send",
            json=task_payload,
            timeout=15
        )
        
        if response.status_code == 200:
            return response.json()
    except Exception as e:
        print(f"❌ Failed to send task to {agent_url}: {e}")
    return None

def start_agent_server(app: FastAPI, port: int):
    """Start agent server in background thread"""
    def run_server():
        uvicorn.run(app, host="127.0.0.1", port=port, log_level="error")
    
    thread = threading.Thread(target=run_server, daemon=True)
    thread.start()
    return thread

def main():
    """Main multi-agent demonstration"""
    print("🚀 Starting Multi-Agent A2A Communication Demo...")
    
    # Define specialized agents
    agents = [
        {
            "id": "data-analyst-001",
            "name": "DataAnalyst Agent", 
            "description": "Specializes in data analysis and insights",
            "capabilities": ["data_analysis", "statistics", "visualization"],
            "port": 8001
        },
        {
            "id": "content-writer-001", 
            "name": "ContentWriter Agent",
            "description": "Specializes in content creation and writing",
            "capabilities": ["content_writing", "editing", "marketing"],
            "port": 8002
        },
        {
            "id": "code-reviewer-001",
            "name": "CodeReviewer Agent", 
            "description": "Specializes in code review and software engineering",
            "capabilities": ["code_review", "software_engineering", "debugging"],
            "port": 8003
        }
    ]
    
    # Start all agents
    print(f"\n🤖 Starting {len(agents)} specialized agents...")
    for agent in agents:
        app = create_agent(
            agent["id"],
            agent["name"], 
            agent["description"],
            agent["capabilities"],
            agent["port"]
        )
        start_agent_server(app, agent["port"])
        agent["url"] = f"http://127.0.0.1:{agent['port']}"
        print(f"   ✅ {agent['name']}: {agent['url']}")
    
    # Wait for agents to start
    time.sleep(3)
    
    # Discover all agents
    print(f"\n🔍 Discovering agents via A2A protocol...")
    discovered_agents = []
    for agent in agents:
        agent_card = discover_agent(agent["url"])
        if agent_card:
            discovered_agents.append(agent_card)
            print(f"   ✅ {agent_card['name']}: {agent_card['capabilities']}")
    
    # Demonstrate agent-to-agent communication
    if len(discovered_agents) >= 2:
        print(f"\n💬 Demonstrating A2A communication workflow...")
        
        # DataAnalyst analyzes data
        analyst_url = agents[0]["url"]  # DataAnalyst
        writer_url = agents[1]["url"]   # ContentWriter
        
        print(f"📊 Step 1: DataAnalyst analyzes sales data...")
        analyst_result = send_a2a_task(
            analyst_url,
            "Analyze this data trend: Sales increased 25% last quarter. What insights can you provide?"
        )
        
        if analyst_result and analyst_result.get("status", {}).get("state") == "completed":
            # Extract analyst response
            analyst_response = ""
            for msg in analyst_result.get("messages", []):
                if msg.get("role") == "agent":
                    for part in msg.get("parts", []):
                        if part.get("type") == "text":
                            analyst_response += part.get("text", "")
            
            print(f"   📈 Analyst insight: {analyst_response[:100]}...")
            
            # ContentWriter creates content based on analysis
            print(f"✍️  Step 2: ContentWriter creates marketing content...")
            writer_result = send_a2a_task(
                writer_url,
                f"Create a brief marketing summary based on this analysis: {analyst_response[:200]}"
            )
            
            if writer_result and writer_result.get("status", {}).get("state") == "completed":
                writer_response = ""
                for msg in writer_result.get("messages", []):
                    if msg.get("role") == "agent":
                        for part in msg.get("parts", []):
                            if part.get("type") == "text":
                                writer_response += part.get("text", "")
                
                print(f"   📝 Marketing content: {writer_response[:100]}...")
                print(f"\n🎉 Multi-agent A2A workflow completed successfully!")
                print(f"   📊 DataAnalyst → ✍️  ContentWriter pipeline demonstrated")
        
    print(f"\n🌐 Agent endpoints:")
    for agent in agents:
        print(f"   {agent['name']}:")
        print(f"     Agent Card: {agent['url']}/.well-known/agent.json")
        print(f"     Task Endpoint: {agent['url']}/tasks/send")
        print(f"     Health: {agent['url']}/health")
    
    print(f"\n⏰ Agents will run indefinitely. Press Ctrl+C to stop.")
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print(f"\n👋 Shutting down multi-agent demo...")

if __name__ == "__main__":
    main()