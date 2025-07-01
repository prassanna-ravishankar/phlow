"""
Test script for the Python Phlow Agent

This script tests the Python agent's endpoints and demonstrates
how to make authenticated requests between Python agents.
"""

import os
import asyncio
import requests
from typing import Dict, Any

from dotenv import load_dotenv
from phlow_auth import generate_token, AgentCard

# Load environment variables
load_dotenv()

class PythonAgentTester:
    def __init__(self, base_url: str = None):
        self.base_url = base_url or f"http://localhost:{os.getenv('PORT', '8000')}"
        
        # Create a test client agent
        self.client_agent = AgentCard(
            agent_id="test-python-client",
            name="Test Python Client",
            permissions=["read:data", "write:data", "admin:users"],
            public_key=os.getenv("AGENT_PUBLIC_KEY", "").replace("\\n", "\n"),
        )
        
        self.client_private_key = os.getenv("AGENT_PRIVATE_KEY", "").replace("\\n", "\n")
        self.target_agent_id = os.getenv("AGENT_ID")

    def generate_test_token(self, expires_in: str = "1h") -> str:
        """Generate a test token for authentication."""
        return generate_token(
            self.client_agent,
            self.client_private_key,
            self.target_agent_id,
            expires_in
        )

    def make_request(self, method: str, endpoint: str, token: str = None, data: Dict[str, Any] = None) -> requests.Response:
        """Make an HTTP request to the agent."""
        url = f"{self.base_url}{endpoint}"
        headers = {}
        
        if token:
            headers["Authorization"] = f"Bearer {token}"
            headers["X-Phlow-Agent-Id"] = self.client_agent.agent_id
        
        if data:
            headers["Content-Type"] = "application/json"
        
        if method.upper() == "GET":
            return requests.get(url, headers=headers)
        elif method.upper() == "POST":
            return requests.post(url, headers=headers, json=data)
        else:
            raise ValueError(f"Unsupported method: {method}")

    def test_public_endpoints(self):
        """Test public endpoints that don't require authentication."""
        print("🧪 Testing public endpoints...")
        
        # Test root endpoint
        response = self.make_request("GET", "/")
        assert response.status_code == 200, f"Root endpoint failed: {response.status_code}"
        data = response.json()
        print(f"✅ Root endpoint: {data['message']}")
        
        # Test health endpoint
        response = self.make_request("GET", "/health")
        assert response.status_code == 200, f"Health endpoint failed: {response.status_code}"
        data = response.json()
        print(f"✅ Health endpoint: {data['status']}")

    def test_authentication_required(self):
        """Test that protected endpoints require authentication."""
        print("\n🔒 Testing authentication requirements...")
        
        # Test protected endpoint without token
        response = self.make_request("GET", "/protected")
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("✅ Protected endpoint correctly rejects unauthenticated requests")
        
        # Test with invalid token
        response = self.make_request("GET", "/protected", token="invalid-token")
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("✅ Protected endpoint correctly rejects invalid tokens")

    def test_authenticated_endpoints(self):
        """Test endpoints with valid authentication."""
        print("\n🎫 Testing authenticated endpoints...")
        
        token = self.generate_test_token()
        
        # Test protected endpoint
        response = self.make_request("GET", "/protected", token=token)
        assert response.status_code == 200, f"Protected endpoint failed: {response.status_code}"
        data = response.json()
        print(f"✅ Protected endpoint: {data['message']}")
        print(f"   Requesting agent: {data['requesting_agent']['name']}")
        
        # Test agent info endpoint
        response = self.make_request("GET", "/agent-info", token=token)
        assert response.status_code == 200, f"Agent info failed: {response.status_code}"
        data = response.json()
        print(f"✅ Agent info: Retrieved info for {data['agent']['name']}")

    def test_permission_based_access(self):
        """Test permission-based access control."""
        print("\n🔐 Testing permission-based access...")
        
        token = self.generate_test_token()
        
        # Test data read endpoint (requires read:data)
        response = self.make_request("GET", "/data", token=token)
        if "read:data" in self.client_agent.permissions:
            assert response.status_code == 200, f"Data read failed: {response.status_code}"
            data = response.json()
            print(f"✅ Data read: {len(data['data']['users'])} users retrieved")
        else:
            assert response.status_code == 403, f"Expected 403, got {response.status_code}"
            print("✅ Data read correctly denied (insufficient permissions)")
        
        # Test data write endpoint (requires write:data)
        test_data = {"name": "Test User", "email": "test@example.com"}
        response = self.make_request("POST", "/data", token=token, data=test_data)
        if "write:data" in self.client_agent.permissions:
            assert response.status_code == 200, f"Data write failed: {response.status_code}"
            data = response.json()
            print(f"✅ Data write: Created data for {data['received_data']['name']}")
        else:
            assert response.status_code == 403, f"Expected 403, got {response.status_code}"
            print("✅ Data write correctly denied (insufficient permissions)")
        
        # Test admin endpoint (requires admin:users)
        response = self.make_request("GET", "/admin", token=token)
        if "admin:users" in self.client_agent.permissions:
            assert response.status_code == 200, f"Admin endpoint failed: {response.status_code}"
            data = response.json()
            print(f"✅ Admin access: System status is {data['admin_data']['system_status']}")
        else:
            assert response.status_code == 403, f"Expected 403, got {response.status_code}"
            print("✅ Admin access correctly denied (insufficient permissions)")

    def test_token_generation(self):
        """Test token generation endpoint."""
        print("\n🎯 Testing token generation...")
        
        token = self.generate_test_token()
        
        # Generate token for another agent
        request_data = {
            "target_agent_id": "target-agent-123",
            "expires_in": "30m"
        }
        
        response = self.make_request("POST", "/generate-token", token=token, data=request_data)
        assert response.status_code == 200, f"Token generation failed: {response.status_code}"
        
        data = response.json()
        print(f"✅ Token generation: Generated token for {data['target_agent_id']}")
        print(f"   Token expires in: {data['expires_in']}")
        print(f"   Token preview: {data['token'][:50]}...")

    def test_error_handling(self):
        """Test error handling scenarios."""
        print("\n❌ Testing error handling...")
        
        # Test missing agent ID header
        headers = {"Authorization": f"Bearer {self.generate_test_token()}"}
        response = requests.get(f"{self.base_url}/protected", headers=headers)
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("✅ Missing agent ID header correctly handled")
        
        # Test malformed request
        token = self.generate_test_token()
        response = self.make_request("POST", "/generate-token", token=token, data={})
        assert response.status_code == 400, f"Expected 400, got {response.status_code}"
        print("✅ Malformed request correctly handled")

    def test_server_availability(self) -> bool:
        """Test if the server is running."""
        try:
            response = requests.get(f"{self.base_url}/health", timeout=5)
            return response.status_code == 200
        except requests.exceptions.RequestException:
            return False

    def run_all_tests(self):
        """Run all test scenarios."""
        print("🐍 Python Phlow Agent Integration Tests")
        print("=" * 50)
        
        # Check if server is running
        if not self.test_server_availability():
            print("❌ Server is not running. Please start the agent first:")
            print("   python main.py")
            return False
        
        try:
            self.test_public_endpoints()
            self.test_authentication_required()
            self.test_authenticated_endpoints()
            self.test_permission_based_access()
            self.test_token_generation()
            self.test_error_handling()
            
            print("\n🎉 All tests passed successfully!")
            return True
            
        except AssertionError as e:
            print(f"\n❌ Test failed: {e}")
            return False
        except Exception as e:
            print(f"\n💥 Unexpected error: {e}")
            return False

async def test_async_functionality():
    """Test async functionality of the Phlow library."""
    print("\n🔄 Testing async functionality...")
    
    from phlow_auth import PhlowMiddleware, PhlowConfig, AgentCard
    
    # Create test configuration
    config = PhlowConfig(
        supabase_url=os.getenv("SUPABASE_URL"),
        supabase_anon_key=os.getenv("SUPABASE_ANON_KEY"),
        agent_card=AgentCard(
            agent_id="async-test-agent",
            name="Async Test Agent",
            permissions=["read:data"],
            public_key=os.getenv("AGENT_PUBLIC_KEY", "").replace("\\n", "\n"),
        ),
        private_key=os.getenv("AGENT_PRIVATE_KEY", "").replace("\\n", "\n"),
    )
    
    middleware = PhlowMiddleware(config)
    
    # Test token generation
    token = generate_token(
        config.agent_card,
        config.private_key,
        "test-target",
        "1h"
    )
    
    print(f"✅ Async token generation successful")
    print(f"   Token length: {len(token)} characters")

def main():
    """Main test function."""
    # Check required environment variables
    required_vars = ["SUPABASE_URL", "SUPABASE_ANON_KEY", "AGENT_ID", "AGENT_PUBLIC_KEY", "AGENT_PRIVATE_KEY"]
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        print("❌ Missing required environment variables:")
        for var in missing_vars:
            print(f"   {var}")
        print("\nPlease copy .env.example to .env and fill in the values.")
        return
    
    # Run synchronous tests
    tester = PythonAgentTester()
    success = tester.run_all_tests()
    
    # Run async tests
    if success:
        asyncio.run(test_async_functionality())
    
    print("\n" + "=" * 50)
    if success:
        print("🎊 All Python agent tests completed successfully!")
    else:
        print("💔 Some tests failed. Please check the output above.")

if __name__ == "__main__":
    main()