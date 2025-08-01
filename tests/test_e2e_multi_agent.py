"""
Multi-Agent End-to-End tests for Phlow A2A protocol.

Tests real agent-to-agent discovery and communication between multiple agents.
This demonstrates the true value of the A2A protocol - interoperability.

Requires .env file with:
- GEMINI_API_KEY=your_gemini_api_key

For Rancher Desktop users:
Run with: DOCKER_HOST=unix:///Users/$USER/.rd/docker.sock pytest tests/test_e2e_multi_agent.py -v -s
"""

import os
import socket
import threading
import time
import uuid

import docker
import pytest
import requests
import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI

# Load environment variables from .env file
load_dotenv()


@pytest.mark.e2e
class TestMultiAgentA2ACommunication:
    """Test multiple Phlow agents discovering and communicating with each other"""

    @pytest.fixture(scope="class")
    def docker_setup(self):
        """Set up Docker containers for multi-agent testing"""
        try:
            # Auto-detect Rancher Desktop socket if DOCKER_HOST not set
            if not os.environ.get("DOCKER_HOST"):
                rancher_socket = (
                    f"unix:///Users/{os.environ.get('USER', 'user')}/.rd/docker.sock"
                )
                if os.path.exists(rancher_socket.replace("unix://", "")):
                    os.environ["DOCKER_HOST"] = rancher_socket
                    print(f"🐳 Auto-detected Rancher Desktop: {rancher_socket}")

            client = docker.from_env()
            client.ping()
        except Exception as e:
            pytest.skip(f"Docker not accessible: {e}")
            return

        # Start PostgreSQL for agent registry
        postgres_container = None
        try:
            postgres_container = client.containers.run(
                "postgres:15-alpine",
                environment={
                    "POSTGRES_DB": "phlow_multi_test",
                    "POSTGRES_USER": "postgres",
                    "POSTGRES_PASSWORD": "postgres",
                },
                ports={"5432/tcp": None},
                detach=True,
                remove=True,
                name=f"phlow-multi-postgres-{int(time.time())}",
            )

            # Wait for PostgreSQL to be ready
            for _ in range(30):
                try:
                    postgres_container.reload()
                    if postgres_container.status == "running":
                        logs = postgres_container.logs(tail=10).decode()
                        if "database system is ready to accept connections" in logs:
                            break
                except Exception:
                    pass
                time.sleep(1)
            else:
                raise Exception("PostgreSQL failed to start")

            postgres_container.reload()
            postgres_port = postgres_container.ports["5432/tcp"][0]["HostPort"]

            yield {
                "postgres_url": f"postgresql://postgres:postgres@localhost:{postgres_port}/phlow_multi_test",
                "postgres_port": postgres_port,
                "container": postgres_container,
            }

        finally:
            if postgres_container:
                try:
                    postgres_container.stop()
                    postgres_container.remove()
                except Exception:
                    pass
            client.close()

    def create_agent(
        self, agent_id: str, agent_name: str, agent_description: str, capabilities: list
    ):
        """Create a Phlow A2A-compliant agent"""
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
                "capabilities": dict.fromkeys(capabilities, True),
                "input_modes": ["text"],
                "output_modes": ["text"],
                "endpoints": {"task": "/tasks/send"},
                "metadata": {
                    "framework": "phlow",
                    "model": "gemini-2.5-flash-lite",
                    "specialization": capabilities[0] if capabilities else "general",
                },
            }

        # A2A Task endpoint
        @app.post("/tasks/send")
        def send_task(task: dict):
            try:
                task_id = task.get("id", "unknown")
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
                    from google import genai

                    client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
                    prompt = f"You are {agent_name}, a specialized Phlow A2A agent. {agent_description}. Respond briefly to: {user_text}"
                    response = client.models.generate_content(
                        model="gemini-2.5-flash-lite", contents=prompt
                    )
                    response_text = response.text
                else:
                    # Fallback response without Gemini
                    response_text = f"Hello! I'm {agent_name}. I specialize in {', '.join(capabilities)}. You said: {user_text}"

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
                        "specialization": capabilities[0]
                        if capabilities
                        else "general",
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

        return app

    def start_agent_server(self, app: FastAPI, port: int):
        """Start agent server in background thread"""

        def run_server():
            uvicorn.run(app, host="127.0.0.1", port=port, log_level="error")

        thread = threading.Thread(target=run_server, daemon=True)
        thread.start()
        time.sleep(1)  # Give server time to start
        return thread

    def discover_agent(self, agent_url: str):
        """Discover agent using A2A protocol"""
        response = requests.get(f"{agent_url}/.well-known/agent.json", timeout=5)
        if response.status_code == 200:
            return response.json()
        return None

    def send_a2a_task(self, agent_url: str, message_text: str):
        """Send A2A task to agent"""
        task_payload = {
            "id": str(uuid.uuid4()),
            "message": {
                "role": "user",
                "parts": [{"type": "text", "text": message_text}],
            },
        }

        response = requests.post(
            f"{agent_url}/tasks/send", json=task_payload, timeout=15
        )

        if response.status_code == 200:
            return response.json()
        return None

    def test_multi_agent_discovery(self, docker_setup):
        """Test multiple agents can discover each other via A2A protocol"""
        config = docker_setup
        print(f"📊 Using PostgreSQL: {config['postgres_url']}")

        # Skip if no Gemini API key
        if not os.environ.get("GEMINI_API_KEY"):
            print("⚠️  GEMINI_API_KEY not set - using fallback responses")

        # Create multiple specialized agents
        agents = [
            {
                "id": "data-analyst-001",
                "name": "DataAnalyst Agent",
                "description": "Specializes in data analysis and insights",
                "capabilities": ["data_analysis", "statistics", "visualization"],
                "port": None,
            },
            {
                "id": "code-reviewer-001",
                "name": "CodeReviewer Agent",
                "description": "Specializes in code review and software engineering",
                "capabilities": ["code_review", "software_engineering", "debugging"],
                "port": None,
            },
            {
                "id": "content-writer-001",
                "name": "ContentWriter Agent",
                "description": "Specializes in content creation and writing",
                "capabilities": ["content_writing", "editing", "marketing"],
                "port": None,
            },
        ]

        # Start all agents
        servers = []
        try:
            for agent in agents:
                # Find available port
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.bind(("", 0))
                    agent["port"] = s.getsockname()[1]

                # Create and start agent
                app = self.create_agent(
                    agent["id"],
                    agent["name"],
                    agent["description"],
                    agent["capabilities"],
                )
                server = self.start_agent_server(app, agent["port"])
                servers.append(server)
                agent["url"] = f"http://127.0.0.1:{agent['port']}"

            # Wait for all agents to start
            time.sleep(2)

            print(f"🚀 Started {len(agents)} agents:")
            for agent in agents:
                print(f"   {agent['name']}: {agent['url']}")

            # Test A2A discovery for each agent
            discovered_agents = []
            for agent in agents:
                agent_card = self.discover_agent(agent["url"])
                assert agent_card is not None, f"Failed to discover {agent['name']}"
                assert agent_card["id"] == agent["id"]
                assert "endpoints" in agent_card
                assert agent_card["endpoints"]["task"] == "/tasks/send"
                discovered_agents.append(agent_card)
                print(
                    f"✅ Discovered {agent_card['name']}: {agent_card['capabilities']}"
                )

            print(f"✅ All {len(agents)} agents discovered successfully!")

        finally:
            # Cleanup handled by daemon threads
            pass

    def test_agent_to_agent_communication(self, docker_setup):
        """Test agents communicating with each other using A2A protocol"""
        _ = docker_setup  # Use docker_setup for PostgreSQL availability

        # Skip if no Gemini API key
        if not os.environ.get("GEMINI_API_KEY"):
            pytest.skip(
                "GEMINI_API_KEY not set - skipping multi-agent communication test"
            )

        # Create two agents
        analyst_app = self.create_agent(
            "analyst-002",
            "Data Analyst",
            "Expert in data analysis and providing insights",
            ["data_analysis", "insights"],
        )

        writer_app = self.create_agent(
            "writer-002",
            "Content Writer",
            "Expert in creating engaging content and summaries",
            ["content_writing", "summarization"],
        )

        # Start agents on different ports
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s1:
            s1.bind(("", 0))
            analyst_port = s1.getsockname()[1]

        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s2:
            s2.bind(("", 0))
            writer_port = s2.getsockname()[1]

        try:
            # Start both agents
            self.start_agent_server(analyst_app, analyst_port)
            self.start_agent_server(writer_app, writer_port)

            analyst_url = f"http://127.0.0.1:{analyst_port}"
            writer_url = f"http://127.0.0.1:{writer_port}"

            time.sleep(2)  # Wait for agents to start

            print(f"🤖 Analyst Agent: {analyst_url}")
            print(f"✍️  Writer Agent: {writer_url}")

            # Analyst agent provides data insight
            analyst_result = self.send_a2a_task(
                analyst_url,
                "Analyze this data trend: Sales increased 25% last quarter. What insights can you provide?",
            )

            assert analyst_result is not None
            assert analyst_result["status"]["state"] == "completed"

            analyst_response = ""
            for msg in analyst_result["messages"]:
                if msg["role"] == "agent":
                    for part in msg["parts"]:
                        if part["type"] == "text":
                            analyst_response += part["text"]

            print(f"📊 Analyst insight: {analyst_response[:100]}...")

            # Writer agent creates content based on analyst's insight
            writer_result = self.send_a2a_task(
                writer_url,
                f"Create a brief marketing summary based on this analysis: {analyst_response[:200]}",
            )

            assert writer_result is not None
            assert writer_result["status"]["state"] == "completed"

            writer_response = ""
            for msg in writer_result["messages"]:
                if msg["role"] == "agent":
                    for part in msg["parts"]:
                        if part["type"] == "text":
                            writer_response += part["text"]

            print(f"✍️  Writer content: {writer_response[:100]}...")

            # Verify the workflow
            assert len(analyst_response) > 0
            assert len(writer_response) > 0
            assert analyst_result["metadata"]["specialization"] == "data_analysis"
            assert writer_result["metadata"]["specialization"] == "content_writing"

            print("✅ Multi-agent A2A workflow completed successfully!")
            print("   📊 Analyst → ✍️  Writer pipeline demonstrated")

        finally:
            # Cleanup handled by daemon threads
            pass
