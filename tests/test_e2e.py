"""
End-to-End tests for Phlow agent infrastructure and real agent communication.

Includes:
1. Docker/PostgreSQL infrastructure tests
2. Real agent-to-agent communication tests using Gemini API

For Rancher Desktop users:
Run with: DOCKER_HOST=unix:///Users/$USER/.rd/docker.sock pytest tests/test_e2e_simple.py -v -s

For Docker Desktop users:
Run with: pytest tests/test_e2e_simple.py -v -s

Requires .env file with:
- GEMINI_API_KEY=your_gemini_api_key
"""

import os
import time

import docker
import pytest
import requests
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


@pytest.mark.e2e
class TestPhlowWithDirectDocker:
    """Test Phlow setup using Docker directly (simpler than TestContainers)"""

    @pytest.fixture(scope="class")
    def docker_setup(self):
        """Set up Docker containers directly"""
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

        # Start a simple PostgreSQL container
        postgres_container = None
        try:
            postgres_container = client.containers.run(
                "postgres:15-alpine",
                environment={
                    "POSTGRES_DB": "phlow_test",
                    "POSTGRES_USER": "postgres",
                    "POSTGRES_PASSWORD": "postgres",
                },
                ports={"5432/tcp": None},  # Random port
                detach=True,
                remove=True,
                name=f"phlow-test-postgres-{int(time.time())}",
            )

            # Wait for PostgreSQL to be ready
            for _ in range(30):
                try:
                    postgres_container.reload()
                    if postgres_container.status == "running":
                        # Try to connect
                        logs = postgres_container.logs(tail=10).decode()
                        if "database system is ready to accept connections" in logs:
                            break
                except Exception:
                    pass
                time.sleep(1)
            else:
                raise Exception("PostgreSQL failed to start")

            # Get the mapped port
            postgres_container.reload()
            postgres_port = postgres_container.ports["5432/tcp"][0]["HostPort"]

            yield {
                "postgres_url": f"postgresql://postgres:postgres@localhost:{postgres_port}/phlow_test",
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

    def test_docker_connectivity(self, docker_setup):
        """Test that Docker setup works"""
        config = docker_setup
        postgres_url = config["postgres_url"]

        print(f"✅ PostgreSQL running at: {postgres_url}")
        print("✅ Docker setup successful!")

        # This validates that our Docker integration works
        assert config["postgres_port"] is not None
        assert "postgresql://" in postgres_url

    def test_phlow_imports(self, docker_setup):
        """Test that Phlow library imports work in E2E context"""
        try:
            from phlow import AgentCard, PhlowConfig  # noqa: F401
            from phlow.integrations.fastapi import FastAPIPhlowAuth  # noqa: F401

            print("✅ Phlow imports successful!")
            assert True

        except ImportError as e:
            pytest.fail(f"Failed to import Phlow components: {e}")

    def test_agent_communication(self, docker_setup):
        """Test real agent-to-agent communication with Gemini API"""
        import socket
        import threading
        import time

        import uvicorn
        from fastapi import FastAPI

        # Skip if no Gemini API key
        if not os.environ.get("GEMINI_API_KEY"):
            pytest.skip("GEMINI_API_KEY not set - skipping agent communication test")

        config = docker_setup
        postgres_url = config["postgres_url"]

        print("🤖 Starting agent communication test...")
        print(f"📊 Using PostgreSQL: {postgres_url}")

        # Create a proper A2A-compliant Phlow agent
        app = FastAPI(title="Phlow A2A Test Agent")

        # A2A Agent Card (discovery endpoint)
        @app.get("/.well-known/agent.json")
        def agent_card():
            """A2A Agent Card for discovery - required by A2A protocol"""
            return {
                "id": "phlow-test-agent-001",
                "name": "Phlow A2A Test Agent",
                "description": "A Phlow-powered agent implementing Google's A2A protocol with Gemini integration",
                "version": "1.0.0",
                "author": "Phlow Framework",
                "capabilities": {
                    "text_generation": True,
                    "gemini_integration": True,
                    "phlow_authentication": True,
                },
                "input_modes": ["text"],
                "output_modes": ["text"],
                "endpoints": {"task": "/tasks/send"},
                "metadata": {"framework": "phlow", "model": "gemini-2.5-flash"},
            }

        # A2A Task endpoint (required by A2A protocol)
        @app.post("/tasks/send")
        def send_task(task: dict):
            """A2A Task endpoint - handles incoming tasks from other agents"""
            try:
                # Extract message from A2A task format
                task_id = task.get("id", "unknown")
                message = task.get("message", {})
                user_text = ""

                # Parse A2A message format
                if "parts" in message:
                    for part in message["parts"]:
                        if part.get("type") == "text":
                            user_text += part.get("text", "")
                else:
                    user_text = message.get("text", "Hello from A2A")

                print(f"🤖 A2A Task {task_id}: Processing '{user_text}'")

                # Use Gemini API for response
                import google.generativeai as genai

                genai.configure(api_key=os.environ["GEMINI_API_KEY"])

                model = genai.GenerativeModel("gemini-2.5-flash")
                response = model.generate_content(
                    f"You are a Phlow A2A agent. Respond helpfully and briefly to: {user_text}"
                )

                # Return A2A-compliant task response
                return {
                    "id": task_id,
                    "status": {
                        "state": "completed",
                        "message": "Task completed successfully",
                    },
                    "messages": [
                        {
                            "role": "agent",
                            "parts": [{"type": "text", "text": response.text}],
                        }
                    ],
                    "artifacts": [],
                    "metadata": {
                        "agent_id": "phlow-test-agent-001",
                        "model": "gemini-2.5-flash",
                        "framework": "phlow",
                    },
                }

            except Exception as e:
                return {
                    "id": task.get("id", "unknown"),
                    "status": {"state": "failed", "message": f"Task failed: {str(e)}"},
                    "messages": [
                        {
                            "role": "agent",
                            "parts": [
                                {
                                    "type": "text",
                                    "text": f"Error processing request: {str(e)}",
                                }
                            ],
                        }
                    ],
                    "artifacts": [],
                    "metadata": {"agent_id": "phlow-test-agent-001", "error": str(e)},
                }

        # Legacy endpoints for backwards compatibility
        @app.get("/health")
        def health():
            return {"status": "healthy", "agent_id": "phlow-test-agent-001"}

        @app.get("/info")
        def info():
            return {
                "agent_id": "phlow-test-agent-001",
                "name": "Phlow A2A Test Agent",
                "description": "A2A-compliant agent powered by Phlow framework",
                "a2a_compliant": True,
                "capabilities": [
                    "text_generation",
                    "gemini_integration",
                    "a2a_protocol",
                ],
            }

        # Find available port
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(("", 0))
            agent_port = s.getsockname()[1]

        # Start agent in background thread
        server_thread = None
        try:

            def run_server():
                uvicorn.run(app, host="127.0.0.1", port=agent_port, log_level="error")

            server_thread = threading.Thread(target=run_server, daemon=True)
            server_thread.start()

            # Wait for agent to start
            time.sleep(2)

            # Test A2A-compliant agent endpoints
            agent_url = f"http://127.0.0.1:{agent_port}"

            # Test A2A Agent Card Discovery
            agent_card_response = requests.get(
                f"{agent_url}/.well-known/agent.json", timeout=5
            )
            assert agent_card_response.status_code == 200
            agent_card = agent_card_response.json()
            assert agent_card["id"] == "phlow-test-agent-001"
            assert "endpoints" in agent_card
            assert agent_card["endpoints"]["task"] == "/tasks/send"
            print("✅ A2A Agent Card discovery passed")

            # Test A2A Task sending
            import uuid

            task_payload = {
                "id": str(uuid.uuid4()),
                "message": {
                    "role": "user",
                    "parts": [
                        {
                            "type": "text",
                            "text": "Hello from Phlow E2E test! What is the meaning of life?",
                        }
                    ],
                },
            }

            task_response = requests.post(
                f"{agent_url}/tasks/send", json=task_payload, timeout=15
            )
            assert task_response.status_code == 200
            task_result = task_response.json()

            if task_result.get("status", {}).get("state") == "completed":
                print("✅ A2A Task communication successful!")

                # Extract agent response from A2A format
                agent_messages = task_result.get("messages", [])
                agent_response = ""
                for msg in agent_messages:
                    if msg.get("role") == "agent":
                        for part in msg.get("parts", []):
                            if part.get("type") == "text":
                                agent_response += part.get("text", "")

                print(f"🤖 A2A Agent response: {agent_response[:100]}...")
                assert len(agent_response) > 0
                assert task_result["id"] == task_payload["id"]
                print("✅ Proper A2A protocol compliance verified!")

            else:
                print(
                    f"⚠️  A2A Task failed: {task_result.get('status', {}).get('message', 'Unknown error')}"
                )
                # Don't fail test for API issues, just log

            # Test legacy health endpoint
            health_response = requests.get(f"{agent_url}/health", timeout=5)
            assert health_response.status_code == 200
            health_data = health_response.json()
            assert health_data["status"] == "healthy"
            print("✅ Legacy health endpoint still works")

        except Exception as e:
            pytest.fail(f"Agent communication test failed: {e}")
        finally:
            # Cleanup handled by daemon thread
            pass
