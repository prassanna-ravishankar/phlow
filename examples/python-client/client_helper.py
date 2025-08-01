"""
Python Client Helper for Phlow Authentication

This module provides utilities for Python clients to authenticate
with other Phlow agents and make secure requests.
"""

import os
import requests
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from datetime import datetime

from phlow import generate_token, AgentCard, verify_token


@dataclass
class PhlowClientConfig:
    """Configuration for Phlow client."""
    agent_card: AgentCard
    private_key: str
    base_timeout: int = 30
    retry_attempts: int = 3


class PhlowClient:
    """
    Python client for making authenticated requests to other Phlow agents.
    
    This client handles token generation, request authentication,
    and provides convenience methods for common operations.
    """
    
    def __init__(self, config: PhlowClientConfig):
        """Initialize the Phlow client.
        
        Args:
            config: Client configuration including agent card and private key
        """
        self.config = config
        self.session = requests.Session()
        self.session.timeout = config.base_timeout
        
        # Set default headers
        self.session.headers.update({
            "Content-Type": "application/json",
            "User-Agent": f"PhlowClient/1.0 ({config.agent_card.metadata.get('agent_id', 'unknown')})",
            "X-Phlow-Agent-Id": config.agent_card.metadata.get('agent_id', 'unknown'),
        })
    
    def generate_token(self, target_agent_id: str, expires_in: str = "1h") -> str:
        """Generate an authentication token for a target agent.
        
        Args:
            target_agent_id: ID of the target agent
            expires_in: Token expiration time (e.g., "1h", "30m")
            
        Returns:
            JWT token string
        """
        return generate_token(
            self.config.agent_card,
            self.config.private_key,
            target_agent_id,
            expires_in
        )
    
    def make_request(
        self,
        method: str,
        url: str,
        target_agent_id: str,
        data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
        token_expires_in: str = "1h",
        **kwargs
    ) -> requests.Response:
        """Make an authenticated request to another agent.
        
        Args:
            method: HTTP method (GET, POST, PUT, DELETE)
            url: Full URL to the target endpoint
            target_agent_id: ID of the target agent
            data: Request body data (for POST/PUT)
            params: URL parameters
            token_expires_in: Token expiration time
            **kwargs: Additional arguments passed to requests
            
        Returns:
            HTTP response object
            
        Raises:
            requests.RequestException: If the request fails
        """
        # Generate authentication token
        token = self.generate_token(target_agent_id, token_expires_in)
        
        # Set authentication header
        headers = kwargs.get("headers", {})
        headers["Authorization"] = f"Bearer {token}"
        kwargs["headers"] = headers
        
        # Make the request
        response = self.session.request(
            method=method.upper(),
            url=url,
            json=data,
            params=params,
            **kwargs
        )
        
        return response
    
    def get(self, url: str, target_agent_id: str, **kwargs) -> requests.Response:
        """Make an authenticated GET request."""
        return self.make_request("GET", url, target_agent_id, **kwargs)
    
    def post(self, url: str, target_agent_id: str, data: Dict[str, Any], **kwargs) -> requests.Response:
        """Make an authenticated POST request."""
        return self.make_request("POST", url, target_agent_id, data=data, **kwargs)
    
    def put(self, url: str, target_agent_id: str, data: Dict[str, Any], **kwargs) -> requests.Response:
        """Make an authenticated PUT request."""
        return self.make_request("PUT", url, target_agent_id, data=data, **kwargs)
    
    def delete(self, url: str, target_agent_id: str, **kwargs) -> requests.Response:
        """Make an authenticated DELETE request."""
        return self.make_request("DELETE", url, target_agent_id, **kwargs)
    
    def check_agent_health(self, base_url: str, target_agent_id: str) -> Dict[str, Any]:
        """Check the health of a target agent.
        
        Args:
            base_url: Base URL of the target agent
            target_agent_id: ID of the target agent
            
        Returns:
            Health status information
        """
        try:
            response = self.get(f"{base_url}/health", target_agent_id)
            response.raise_for_status()
            return {
                "status": "healthy",
                "details": response.json(),
                "response_time_ms": response.elapsed.total_seconds() * 1000,
            }
        except requests.exceptions.RequestException as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "response_time_ms": None,
            }
    
    def get_agent_info(self, base_url: str, target_agent_id: str) -> Dict[str, Any]:
        """Get information about a target agent.
        
        Args:
            base_url: Base URL of the target agent
            target_agent_id: ID of the target agent
            
        Returns:
            Agent information
        """
        response = self.get(f"{base_url}/", target_agent_id)
        response.raise_for_status()
        return response.json()
    
    def test_authentication(self, base_url: str, target_agent_id: str) -> bool:
        """Test authentication with a target agent.
        
        Args:
            base_url: Base URL of the target agent
            target_agent_id: ID of the target agent
            
        Returns:
            True if authentication succeeds, False otherwise
        """
        try:
            response = self.get(f"{base_url}/protected", target_agent_id)
            return response.status_code == 200
        except:
            return False
    
    def batch_request(
        self,
        requests_data: List[Dict[str, Any]],
        target_agent_id: str
    ) -> List[Dict[str, Any]]:
        """Make multiple requests in batch.
        
        Args:
            requests_data: List of request configurations
            target_agent_id: ID of the target agent
            
        Returns:
            List of response data with results
        """
        results = []
        
        for req_data in requests_data:
            try:
                response = self.make_request(
                    method=req_data["method"],
                    url=req_data["url"],
                    target_agent_id=target_agent_id,
                    data=req_data.get("data"),
                    params=req_data.get("params"),
                )
                
                results.append({
                    "request": req_data,
                    "success": True,
                    "status_code": response.status_code,
                    "data": response.json() if response.headers.get("content-type", "").startswith("application/json") else response.text,
                    "response_time_ms": response.elapsed.total_seconds() * 1000,
                })
            except Exception as e:
                results.append({
                    "request": req_data,
                    "success": False,
                    "error": str(e),
                    "response_time_ms": None,
                })
        
        return results


class AgentDiscovery:
    """Helper class for discovering and managing agent connections."""
    
    def __init__(self, client: PhlowClient):
        """Initialize agent discovery.
        
        Args:
            client: Phlow client instance
        """
        self.client = client
        self.known_agents: Dict[str, Dict[str, Any]] = {}
    
    def discover_agent(self, base_url: str, agent_id: str) -> Dict[str, Any]:
        """Discover and register information about an agent.
        
        Args:
            base_url: Base URL of the agent
            agent_id: Expected agent ID
            
        Returns:
            Agent discovery information
        """
        try:
            # Get agent information
            agent_info = self.client.get_agent_info(base_url, agent_id)
            
            # Check health
            health_info = self.client.check_agent_health(base_url, agent_id)
            
            # Test authentication
            auth_works = self.client.test_authentication(base_url, agent_id)
            
            discovery_result = {
                "agent_id": agent_id,
                "base_url": base_url,
                "info": agent_info,
                "health": health_info,
                "authentication_works": auth_works,
                "discovered_at": datetime.utcnow().isoformat(),
            }
            
            # Cache the result
            self.known_agents[agent_id] = discovery_result
            
            return discovery_result
            
        except Exception as e:
            error_result = {
                "agent_id": agent_id,
                "base_url": base_url,
                "error": str(e),
                "discovered_at": datetime.utcnow().isoformat(),
            }
            
            self.known_agents[agent_id] = error_result
            return error_result
    
    def get_agent_capabilities(self, agent_id: str) -> List[str]:
        """Get the capabilities/permissions of a known agent.
        
        Args:
            agent_id: Agent ID
            
        Returns:
            List of agent capabilities/permissions
        """
        agent_data = self.known_agents.get(agent_id)
        if not agent_data or "error" in agent_data:
            return []
        
        return agent_data.get("info", {}).get("agent", {}).get("permissions", [])
    
    def find_agents_with_capability(self, capability: str) -> List[str]:
        """Find agents that have a specific capability.
        
        Args:
            capability: Required capability/permission
            
        Returns:
            List of agent IDs that have the capability
        """
        matching_agents = []
        
        for agent_id, agent_data in self.known_agents.items():
            if "error" not in agent_data:
                capabilities = self.get_agent_capabilities(agent_id)
                if capability in capabilities:
                    matching_agents.append(agent_id)
        
        return matching_agents
    
    def get_healthy_agents(self) -> List[str]:
        """Get list of healthy agents.
        
        Returns:
            List of agent IDs that are healthy
        """
        healthy_agents = []
        
        for agent_id, agent_data in self.known_agents.items():
            if ("error" not in agent_data and 
                agent_data.get("health", {}).get("status") == "healthy" and
                agent_data.get("authentication_works", False)):
                healthy_agents.append(agent_id)
        
        return healthy_agents


def create_client_from_env() -> PhlowClient:
    """Create a Phlow client from environment variables.
    
    Returns:
        Configured Phlow client
        
    Raises:
        ValueError: If required environment variables are missing
    """
    required_vars = ["AGENT_ID", "AGENT_NAME", "AGENT_PUBLIC_KEY", "AGENT_PRIVATE_KEY"]
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        raise ValueError(f"Missing required environment variables: {missing_vars}")
    
    # Parse permissions
    permissions = os.getenv("AGENT_PERMISSIONS", "read:data").split(",")
    permissions = [p.strip() for p in permissions if p.strip()]
    
    # Create agent card
    agent_card = AgentCard(
        name=os.getenv("AGENT_NAME"),
        description=os.getenv("AGENT_DESCRIPTION", "Python Phlow client"),
        metadata={
            "agent_id": os.getenv("AGENT_ID"),
            "public_key": os.getenv("AGENT_PUBLIC_KEY").replace("\\n", "\n"),
            "language": "python",
            "client_version": "1.0.0",
        }
    )
    
    # Create configuration
    config = PhlowClientConfig(
        agent_card=agent_card,
        private_key=os.getenv("AGENT_PRIVATE_KEY").replace("\\n", "\n"),
        base_timeout=int(os.getenv("REQUEST_TIMEOUT", "30")),
        retry_attempts=int(os.getenv("RETRY_ATTEMPTS", "3")),
    )
    
    return PhlowClient(config)


# Example usage
if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    
    # Create client from environment
    client = create_client_from_env()
    
    # Example: Discover an agent
    discovery = AgentDiscovery(client)
    result = discovery.discover_agent("http://localhost:8000", "python-agent-001")
    
    print(f"Discovery result: {result}")
    
    # Example: Make authenticated requests
    try:
        response = client.get("http://localhost:8000/protected", "python-agent-001")
        print(f"Protected endpoint response: {response.json()}")
    except Exception as e:
        print(f"Error: {e}")