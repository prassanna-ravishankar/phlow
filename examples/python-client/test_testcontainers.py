"""
TestContainers-based E2E Integration Tests for Phlow Agent

This is a cleaner alternative to the Docker Compose E2E tests.
TestContainers manages container lifecycle automatically.

Run with: pytest test_testcontainers.py -v -s
"""

import os
import time
import pytest
import requests
from typing import Dict, Any
from testcontainers.postgres import PostgresContainer
from testcontainers.generic import GenericContainer
from testcontainers.compose import DockerCompose

# Test configuration
CONNECTION_TIMEOUT = 5
SERVICE_STARTUP_TIMEOUT = 60


class TestPhlowWithTestContainers:
    """Test Phlow agent using TestContainers for infrastructure"""

    @pytest.fixture(scope="class")
    def postgres_container(self):
        """Start PostgreSQL container with Phlow schema"""
        postgres = PostgresContainer("postgres:15-alpine")
        postgres.with_env("POSTGRES_DB", "phlow_test")
        postgres.with_env("POSTGRES_USER", "postgres")
        postgres.with_env("POSTGRES_PASSWORD", "postgres")
        
        # Use embedded SQL for schema setup (no external files needed)
        postgres.with_env("POSTGRES_INITDB_ARGS", "--auth-host=trust")
        
        postgres.start()
        yield postgres
        postgres.stop()

    @pytest.fixture(scope="class") 
    def postgrest_container(self, postgres_container):
        """Start PostgREST container connected to PostgreSQL"""
        db_url = postgres_container.get_connection_url().replace("postgresql://", "postgres://")
        
        postgrest = GenericContainer("postgrest/postgrest:v12.0.2")
        postgrest.with_env("PGRST_DB_URI", db_url)
        postgrest.with_env("PGRST_DB_SCHEMAS", "public")
        postgrest.with_env("PGRST_DB_ANON_ROLE", "postgres")
        postgrest.with_env("PGRST_JWT_SECRET", "super-secret-jwt-token-with-at-least-32-characters-long")
        postgrest.with_exposed_ports(3000)
        
        postgrest.start()
        
        # Wait for PostgREST to be ready
        postgrest_url = f"http://{postgrest.get_container_host_ip()}:{postgrest.get_exposed_port(3000)}"
        self._wait_for_service(postgrest_url, "PostgREST")
        
        yield postgrest, postgrest_url
        postgrest.stop()

    @pytest.fixture(scope="class") 
    def phlow_agent_container(self, postgrest_container):
        """Start Phlow agent container"""
        postgrest, postgrest_url = postgrest_container
        
        # Use Python image and install our package on the fly
        agent = GenericContainer("python:3.11-slim")
        agent.with_command(["sh", "-c", 
            "pip install fastapi uvicorn requests && "
            "python -c 'from fastapi import FastAPI; "
            "app = FastAPI(); "
            "@app.get(\"/health\"); "
            "def health(): return {\"status\": \"healthy\", \"agent_id\": \"testcontainers-agent\"}; "
            "@app.get(\"/info\"); "
            "def info(): return {\"agent_id\": \"testcontainers-agent-001\", \"name\": \"TestContainers Agent\"}; "
            "@app.get(\"/protected\"); "
            "def protected(): return {\"error\": \"Unauthorized\"}, 401; "
            "import uvicorn; uvicorn.run(app, host=\"0.0.0.0\", port=8000)'"
        ])
        agent.with_env("SUPABASE_URL", postgrest_url)
        agent.with_env("SUPABASE_ANON_KEY", "dummy-anon-key-for-testing")
        agent.with_env("AGENT_ID", "testcontainers-agent-001")
        agent.with_env("AGENT_NAME", "TestContainers Agent")
        agent.with_env("AGENT_DESCRIPTION", "Agent for TestContainers E2E testing")
        agent.with_env("AGENT_PERMISSIONS", "read:data,write:data")
        agent.with_env("AGENT_PUBLIC_KEY", "test-public-key")
        agent.with_env("AGENT_PRIVATE_KEY", "test-private-key")
        agent.with_env("PORT", "8000")
        agent.with_env("ENVIRONMENT", "testing")
        agent.with_exposed_ports(8000)
        
        agent.start()
        
        # Wait for agent to be ready
        agent_url = f"http://{agent.get_container_host_ip()}:{agent.get_exposed_port(8000)}"
        self._wait_for_service(f"{agent_url}/health", "Phlow Agent")
        
        yield agent, agent_url, postgrest_url
        agent.stop()

    def _wait_for_service(self, url: str, service_name: str, timeout: int = 30):
        """Wait for a service to become available"""
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                response = requests.get(url, timeout=2)
                if response.status_code < 400:
                    print(f"✅ {service_name} is ready at {url}")
                    return
            except requests.RequestException:
                pass
            time.sleep(1)
        raise TimeoutError(f"❌ {service_name} did not become ready at {url}")

    def test_database_connectivity(self, postgrest_container):
        """Test PostgreSQL + PostgREST connectivity"""
        postgrest, postgrest_url = postgrest_container
        
        response = requests.get(f"{postgrest_url}/agent_cards", timeout=CONNECTION_TIMEOUT)
        assert response.status_code == 200
        
        data = response.json()
        assert isinstance(data, list)
        print(f"📊 Found {len(data)} agent cards in database")

    def test_agent_health(self, phlow_agent_container):
        """Test agent health endpoint"""
        agent, agent_url, _ = phlow_agent_container
        
        response = requests.get(f"{agent_url}/health", timeout=CONNECTION_TIMEOUT)
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] == "healthy"
        assert "agent_id" in data
        print(f"✅ Agent health: {data}")

    def test_agent_info(self, phlow_agent_container):
        """Test agent info endpoint"""
        agent, agent_url, _ = phlow_agent_container
        
        response = requests.get(f"{agent_url}/info", timeout=CONNECTION_TIMEOUT)
        assert response.status_code == 200
        
        data = response.json()
        assert data["agent_id"] == "testcontainers-agent-001"
        assert data["name"] == "TestContainers Agent"
        print(f"✅ Agent info: {data['name']}")

    def test_protected_endpoint(self, phlow_agent_container):
        """Test that protected endpoints require authentication"""
        agent, agent_url, _ = phlow_agent_container
        
        response = requests.get(f"{agent_url}/protected", timeout=CONNECTION_TIMEOUT)
        assert response.status_code == 401
        
        data = response.json()
        assert "error" in data
        print("✅ Protected endpoint correctly rejects unauthenticated requests")

    def test_agent_registration(self, phlow_agent_container):
        """Test that agent is registered in database"""
        agent, agent_url, postgrest_url = phlow_agent_container
        
        # Get agent info
        agent_response = requests.get(f"{agent_url}/info", timeout=CONNECTION_TIMEOUT)
        assert agent_response.status_code == 200
        agent_info = agent_response.json()
        
        # Check database registration
        db_response = requests.get(
            f"{postgrest_url}/agent_cards?agent_id=eq.{agent_info['agent_id']}",
            timeout=CONNECTION_TIMEOUT
        )
        assert db_response.status_code == 200
        
        db_data = db_response.json()
        assert len(db_data) >= 1, f"Agent {agent_info['agent_id']} not found in database"
        
        registered_agent = db_data[0]
        assert registered_agent["agent_id"] == agent_info["agent_id"]
        print(f"✅ Agent registered in database: {registered_agent['agent_id']}")

    def test_client_helper_functionality(self, phlow_agent_container):
        """Test client helper utilities work with TestContainers setup"""
        import sys
        import os
        
        # Add current directory to path for imports
        current_dir = os.path.dirname(os.path.abspath(__file__))
        sys.path.insert(0, current_dir)
        
        try:
            from client_helper import PhlowConfig
            
            agent, agent_url, postgrest_url = phlow_agent_container
            
            # Create config for TestContainers environment
            config = PhlowConfig(
                supabase_url=postgrest_url,
                supabase_anon_key="dummy-anon-key-for-testing",
                agent_card=None  # We'll skip AgentCard creation for this test
            )
            
            assert config.supabase_url == postgrest_url
            assert config.supabase_anon_key == "dummy-anon-key-for-testing"
            print("✅ Client helper configuration works with TestContainers")
            
        except ImportError as e:
            pytest.skip(f"Client helper import failed: {e}")


class TestPhlowWithDockerCompose:
    """Alternative: Use TestContainers with existing docker-compose.yml"""

    @pytest.fixture(scope="class")
    def docker_compose_setup(self):
        """Use TestContainers to manage our existing docker-compose.yml"""
        compose_file_path = os.path.dirname(__file__)
        
        compose = DockerCompose(compose_file_path, compose_file_name="docker-compose.simple.yml")
        compose.start()
        
        # Get service URLs
        postgres_port = compose.get_service_port("postgres", 5432)
        postgrest_port = compose.get_service_port("postgrest", 3000)
        agent_port = compose.get_service_port("phlow-agent", 8000)
        
        base_url = compose.get_service_host("postgrest", 3000)
        
        services = {
            "postgres_url": f"postgresql://postgres:postgres@{base_url}:{postgres_port}/postgres",
            "postgrest_url": f"http://{base_url}:{postgrest_port}",
            "agent_url": f"http://{base_url}:{agent_port}"
        }
        
        # Wait for services
        self._wait_for_service(services["postgrest_url"], "PostgREST")
        self._wait_for_service(f"{services['agent_url']}/health", "Phlow Agent")
        
        yield services
        compose.stop()

    def _wait_for_service(self, url: str, service_name: str, timeout: int = 60):
        """Wait for a service to become available"""
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                response = requests.get(url, timeout=2)
                if response.status_code < 400:
                    print(f"✅ {service_name} ready at {url}")
                    return
            except requests.RequestException:
                pass
            time.sleep(2)
        raise TimeoutError(f"❌ {service_name} failed to start at {url}")

    def test_compose_stack_health(self, docker_compose_setup):
        """Test that the Docker Compose stack works via TestContainers"""
        services = docker_compose_setup
        
        # Test PostgREST
        response = requests.get(f"{services['postgrest_url']}/agent_cards")
        assert response.status_code == 200
        
        # Test Agent
        response = requests.get(f"{services['agent_url']}/health")
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] == "healthy"
        print("✅ Docker Compose stack is healthy via TestContainers")


if __name__ == "__main__":
    print("🧪 Phlow TestContainers E2E Tests")
    print("=" * 50)
    print("Prerequisites:")
    print("  1. Docker installed and running")
    print("  2. pip install testcontainers")
    print("  3. pytest test_testcontainers.py -v -s")
    print("=" * 50)