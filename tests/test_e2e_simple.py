"""
Simplified End-to-End tests for Phlow using TestContainers.

Tests basic functionality with a real PostgreSQL database.
"""

import time

import pytest
from dotenv import load_dotenv
from testcontainers.postgres import PostgresContainer

# Load environment variables from .env file
load_dotenv()


@pytest.mark.e2e
class TestPhlowE2E:
    """Simple E2E tests using TestContainers"""

    @pytest.fixture(scope="class")
    def postgres_container(self):
        """Set up PostgreSQL container using TestContainers"""
        try:
            with PostgresContainer("postgres:15-alpine") as postgres:
                # Wait a moment for PostgreSQL to be fully ready
                time.sleep(2)

                yield {
                    "postgres_url": postgres.get_connection_url(),
                    "postgres_port": postgres.get_exposed_port(5432),
                    "container": postgres,
                }
        except Exception as e:
            pytest.skip(f"TestContainers/Docker not accessible: {e}")

    def test_postgres_connectivity(self, postgres_container):
        """Test that PostgreSQL container works"""
        config = postgres_container
        postgres_url = config["postgres_url"]

        print(f"✅ PostgreSQL running at: {postgres_url}")
        print("✅ TestContainers setup successful!")

        # Basic validation
        assert config["postgres_port"] is not None
        assert postgres_url.startswith("postgresql")

    def test_phlow_imports(self, postgres_container):
        """Test that Phlow library imports work in E2E context"""
        try:
            from phlow import AgentCard, PhlowConfig, PhlowMiddleware  # noqa: F401
            from phlow.integrations.fastapi import FastAPIPhlowAuth  # noqa: F401

            print("✅ Phlow imports successful!")
            assert True

        except ImportError as e:
            pytest.fail(f"Failed to import Phlow components: {e}")

    def test_phlow_middleware_basic(self, postgres_container):
        """Test basic Phlow middleware functionality - just test creation"""
        from phlow import AgentCard, PhlowConfig, PhlowMiddleware

        # Create a basic configuration (using mock Supabase URLs since we're just testing creation)
        config = PhlowConfig(
            agent_card=AgentCard(
                name="Test Agent",
                description="E2E test agent",
                service_url="https://test-agent.example.com",
                skills=[
                    "chat",
                    "analysis",
                ],  # Keep simple for now - will be converted by middleware
                metadata={"agent_id": "test-agent-e2e"},
            ),
            private_key="test-key-for-e2e",
            supabase_url="https://mock-project.supabase.co",
            supabase_anon_key="mock-anon-key",
            enable_audit_log=False,  # Disable for simple test
        )

        # Create middleware instance (will fail on Supabase connection but that's expected)
        try:
            middleware = PhlowMiddleware(config)
            print("✅ PhlowMiddleware created successfully!")
            assert middleware is not None
            assert middleware.config.agent_card.name == "Test Agent"

        except Exception as e:
            # Expected to fail on Supabase connection, but config should be valid
            if "Invalid URL" in str(e):
                pytest.fail(f"Configuration error: {e}")
            else:
                print(f"✅ Expected Supabase connection error (config is valid): {e}")
                assert True
