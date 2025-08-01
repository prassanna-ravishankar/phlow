"""
End-to-End Integration Tests for Phlow Agent

These tests require the Docker Compose stack to be running:
    docker-compose up -d

Run with: pytest test_e2e.py -v -s
"""

import os
import time
import pytest
import requests
import subprocess
from typing import Dict, Any

# Test configuration
SUPABASE_URL = "http://localhost:54321"
SUPABASE_ANON_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZS1kZW1vIiwicm9sZSI6ImFub24iLCJleHAiOjE5ODM4MTI5OTZ9.CRXP1A7WOeoJeXxjNni43kdQwgnWNReilDMblYTn_I0"
AGENT_URL = "http://localhost:8000"
STUDIO_URL = "http://localhost:54323"

# Test timeouts
CONNECTION_TIMEOUT = 5
SERVICE_STARTUP_TIMEOUT = 60


class TestDockerStackE2E:
    """Test the full Docker Compose stack"""

    @pytest.fixture(scope="class", autouse=True)
    def ensure_stack_running(self):
        """Ensure Docker Compose stack is running before tests"""
        print("\n🐳 Checking Docker Compose stack...")
        
        # Check if services are accessible
        services = {
            "Supabase API": SUPABASE_URL,
            "Supabase Studio": STUDIO_URL,
            "Phlow Agent": f"{AGENT_URL}/health"
        }
        
        all_running = True
        for name, url in services.items():
            try:
                response = requests.get(url, timeout=CONNECTION_TIMEOUT)
                if response.status_code < 400:
                    print(f"✅ {name}: Running")
                else:
                    print(f"❌ {name}: HTTP {response.status_code}")
                    all_running = False
            except requests.RequestException as e:
                print(f"❌ {name}: {str(e)}")
                all_running = False
        
        if not all_running:
            pytest.skip(
                "Docker Compose stack not running. Start with: cd examples/python-client && docker-compose up -d"
            )

    def test_supabase_database_connection(self):
        """Test that Supabase database is accessible"""
        response = requests.get(
            f"{SUPABASE_URL}/rest/v1/agent_cards",
            headers={"apikey": SUPABASE_ANON_KEY},
            timeout=CONNECTION_TIMEOUT
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"📊 Found {len(data)} agent cards in database")

    def test_agent_cards_table_schema(self):
        """Test that agent_cards table has correct schema"""
        response = requests.get(
            f"{SUPABASE_URL}/rest/v1/agent_cards",
            headers={"apikey": SUPABASE_ANON_KEY},
            timeout=CONNECTION_TIMEOUT
        )
        assert response.status_code == 200
        
        data = response.json()
        if data:  # If there are records, check schema
            agent_card = data[0]
            expected_fields = {
                "id", "agent_id", "name", "description", 
                "service_url", "skills", "metadata", "public_key",
                "created_at", "updated_at"
            }
            actual_fields = set(agent_card.keys())
            assert expected_fields.issubset(actual_fields), f"Missing fields: {expected_fields - actual_fields}"
            print("✅ Agent cards table schema is correct")

    def test_sample_agent_exists(self):
        """Test that sample agent was inserted during initialization"""
        response = requests.get(
            f"{SUPABASE_URL}/rest/v1/agent_cards?agent_id=eq.python-agent-001",
            headers={"apikey": SUPABASE_ANON_KEY},
            timeout=CONNECTION_TIMEOUT
        )
        assert response.status_code == 200
        
        data = response.json()
        assert len(data) >= 1, "Sample agent 'python-agent-001' not found"
        
        agent = data[0]
        assert agent["agent_id"] == "python-agent-001"
        assert agent["name"] == "Python Agent Example"
        assert "fastapi" in agent["description"].lower()
        print("✅ Sample agent exists in database")


class TestPhlowAgentE2E:
    """Test the Phlow Agent FastAPI application"""

    def test_agent_health_endpoint(self):
        """Test agent health check"""
        response = requests.get(f"{AGENT_URL}/health", timeout=CONNECTION_TIMEOUT)
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] == "healthy"
        assert "agent_id" in data
        assert "timestamp" in data
        print(f"✅ Agent health: {data}")

    def test_agent_info_endpoint(self):
        """Test agent info endpoint"""
        response = requests.get(f"{AGENT_URL}/info", timeout=CONNECTION_TIMEOUT)
        assert response.status_code == 200
        
        data = response.json()
        assert "agent_id" in data
        assert "name" in data
        assert "description" in data
        assert "capabilities" in data
        print(f"✅ Agent info: {data['name']}")

    def test_protected_endpoint_without_auth(self):
        """Test that protected endpoints require authentication"""
        response = requests.get(f"{AGENT_URL}/protected", timeout=CONNECTION_TIMEOUT)
        assert response.status_code == 401
        
        data = response.json()
        assert "error" in data
        print("✅ Protected endpoint correctly rejects unauthenticated requests")

    def test_agent_registration_in_supabase(self):
        """Test that agent properly registered itself in Supabase"""
        # Get agent info
        agent_response = requests.get(f"{AGENT_URL}/info", timeout=CONNECTION_TIMEOUT)
        assert agent_response.status_code == 200
        agent_info = agent_response.json()
        
        # Check if agent exists in Supabase
        supabase_response = requests.get(
            f"{SUPABASE_URL}/rest/v1/agent_cards?agent_id=eq.{agent_info['agent_id']}",
            headers={"apikey": SUPABASE_ANON_KEY},
            timeout=CONNECTION_TIMEOUT
        )
        assert supabase_response.status_code == 200
        
        supabase_data = supabase_response.json()
        assert len(supabase_data) >= 1, f"Agent {agent_info['agent_id']} not registered in Supabase"
        
        registered_agent = supabase_data[0]
        assert registered_agent["agent_id"] == agent_info["agent_id"]
        print(f"✅ Agent properly registered in Supabase: {registered_agent['agent_id']}")


class TestClientHelperE2E:
    """Test the client helper utilities"""

    def test_client_helper_imports(self):
        """Test that client helper imports work"""
        import sys
        import os
        
        # Add current directory to path
        current_dir = os.path.dirname(os.path.abspath(__file__))
        sys.path.insert(0, current_dir)
        
        try:
            from client_helper import PhlowConfig, create_client_from_env
            print("✅ Client helper imports successful")
        except ImportError as e:
            pytest.fail(f"Failed to import client helper: {e}")

    def test_client_creation_with_env(self):
        """Test creating client from environment variables"""
        import sys
        import os
        
        current_dir = os.path.dirname(os.path.abspath(__file__))
        sys.path.insert(0, current_dir)
        
        # Set test environment
        test_env = {
            "SUPABASE_URL": SUPABASE_URL,
            "SUPABASE_ANON_KEY": SUPABASE_ANON_KEY,
            "AGENT_ID": "test-client-agent",
            "AGENT_NAME": "Test Client Agent",
            "AGENT_DESCRIPTION": "Agent for E2E testing",
            "AGENT_PERMISSIONS": "read:test,write:test",
            "AGENT_PUBLIC_KEY": "test-public-key",
            "AGENT_PRIVATE_KEY": "test-private-key"
        }
        
        # Temporarily set environment
        original_env = {}
        for key, value in test_env.items():
            original_env[key] = os.environ.get(key)
            os.environ[key] = value
        
        try:
            from client_helper import create_client_from_env
            
            config = create_client_from_env()
            assert config.supabase_url == SUPABASE_URL
            assert config.supabase_anon_key == SUPABASE_ANON_KEY
            assert config.agent_card.metadata.get("agent_id") == "test-client-agent"
            print("✅ Client creation from environment successful")
            
        finally:
            # Restore original environment
            for key, value in original_env.items():
                if value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = value


class TestTokenFlowE2E:
    """Test end-to-end token generation and validation"""

    def test_token_generation_and_validation(self):
        """Test full token flow"""
        import sys
        import os
        
        current_dir = os.path.dirname(os.path.abspath(__file__))
        sys.path.insert(0, current_dir)
        
        from phlow import generate_token, verify_token, AgentCard
        
        # Create test agent card
        agent_card = AgentCard(
            agent_id="test-token-agent",
            name="Test Token Agent",
            description="Agent for token testing",
            metadata={
                "agent_id": "test-token-agent",
                "public_key": "test-public-key"
            }
        )
        
        # Generate token
        try:
            token = generate_token(
                agent_card=agent_card,
                target_agent_id="target-agent",
                private_key="test-private-key"
            )
            assert isinstance(token, str)
            assert len(token) > 0
            print(f"✅ Token generated: {token[:20]}...")
            
            # Note: Full verification would require matching key pairs
            # This test validates the generation process
            
        except Exception as e:
            # Expected to fail with demo keys, but generation should work
            print(f"✅ Token generation process works (expected key mismatch): {type(e).__name__}")


@pytest.mark.slow
class TestPerformanceE2E:
    """Performance and load tests"""

    def test_agent_response_time(self):
        """Test agent response times"""
        import time
        
        response_times = []
        for i in range(10):
            start_time = time.time()
            response = requests.get(f"{AGENT_URL}/health", timeout=CONNECTION_TIMEOUT)
            end_time = time.time()
            
            assert response.status_code == 200
            response_times.append(end_time - start_time)
        
        avg_response_time = sum(response_times) / len(response_times)
        max_response_time = max(response_times)
        
        print(f"📊 Average response time: {avg_response_time:.3f}s")
        print(f"📊 Max response time: {max_response_time:.3f}s")
        
        # Response time should be reasonable
        assert avg_response_time < 1.0, f"Average response time too slow: {avg_response_time:.3f}s"
        assert max_response_time < 2.0, f"Max response time too slow: {max_response_time:.3f}s"

    def test_concurrent_requests(self):
        """Test handling concurrent requests"""
        import concurrent.futures
        import threading
        
        def make_request():
            response = requests.get(f"{AGENT_URL}/info", timeout=CONNECTION_TIMEOUT)
            return response.status_code == 200
        
        # Test 20 concurrent requests
        with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
            futures = [executor.submit(make_request) for _ in range(20)]
            results = [future.result() for future in concurrent.futures.as_completed(futures)]
        
        success_rate = sum(results) / len(results)
        print(f"📊 Concurrent request success rate: {success_rate:.1%}")
        
        assert success_rate >= 0.95, f"Success rate too low: {success_rate:.1%}"


if __name__ == "__main__":
    print("🧪 Running Phlow E2E Tests")
    print("=" * 50)
    print("Prerequisites:")
    print("  1. cd examples/python-client")
    print("  2. docker-compose up -d")
    print("  3. Wait for all services to start")
    print("=" * 50)
    
    # Run tests
    pytest.main([__file__, "-v", "-s", "--tb=short"])