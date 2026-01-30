"""
RBAC Agent Example

This example demonstrates how to create an agent that uses Phlow's RBAC (Role-Based Access Control)
functionality with Verifiable Credentials.

The agent shows:
1. How to set up role-based authentication
2. How to store and manage role credentials
3. How to respond to role credential requests
4. How to protect endpoints with role requirements

Usage:
    python main.py

Requirements:
    - Supabase project with Phlow schema
    - Environment variables configured
    - Role credentials stored (see setup instructions)
"""

import os

import uvicorn
from fastapi import Depends, FastAPI, HTTPException

# Phlow imports
from phlow import AgentCard, PhlowConfig, PhlowContext, PhlowMiddleware
from phlow.integrations.fastapi import FastAPIPhlowAuth
from phlow.rbac import RoleCredential, RoleCredentialStore
from phlow.rbac.types import (
    CredentialSubject,
    RoleCredentialRequest,
    RoleCredentialResponse,
)

# Configuration
SUPABASE_URL = os.getenv("SUPABASE_URL", "https://your-project.supabase.co")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY", "your-anon-key")
AGENT_ID = os.getenv("AGENT_ID", "rbac-demo-agent")
AGENT_NAME = os.getenv("AGENT_NAME", "RBAC Demo Agent")
PRIVATE_KEY = os.getenv("PRIVATE_KEY", "your-private-key")

# FastAPI app
app = FastAPI(
    title="Phlow RBAC Demo Agent",
    description="Demonstrates role-based access control with Verifiable Credentials",
    version="1.0.0",
)

# Global variables for dependency injection
middleware = None
credential_store = None


async def setup_agent():
    """Set up the agent with Phlow middleware and RBAC capabilities."""
    global middleware, credential_store

    # Create agent card
    agent_card = AgentCard(
        name=AGENT_NAME,
        description="A demo agent showcasing RBAC with Verifiable Credentials",
        service_url="http://localhost:8000",
        skills=[
            {
                "name": "role-based-access",
                "description": "Demonstrates role-based access control",
            },
            {
                "name": "credential-management",
                "description": "Manages verifiable credentials for roles",
            },
        ],
        security_schemes={
            "phlow-jwt": {"type": "http", "scheme": "bearer", "bearerFormat": "JWT"}
        },
        metadata={"agent_id": AGENT_ID},
    )

    # Create Phlow configuration
    config = PhlowConfig(
        supabase_url=SUPABASE_URL,
        supabase_anon_key=SUPABASE_ANON_KEY,
        agent_card=agent_card,
        private_key=PRIVATE_KEY,
    )

    # Initialize middleware
    middleware = PhlowMiddleware(config)

    # Initialize credential store
    credential_store = RoleCredentialStore()

    # Load or create sample credentials
    await setup_sample_credentials()

    # Register message handlers for role credential requests
    await setup_role_handlers()

    print(f"🤖 Agent '{AGENT_NAME}' initialized with RBAC support")
    print(f"📋 Available roles: {await credential_store.get_all_roles()}")


async def setup_sample_credentials():
    """Set up sample role credentials for demonstration."""
    global credential_store

    # Check if we already have credentials
    existing_roles = await credential_store.get_all_roles()
    if existing_roles:
        print(f"📜 Loaded existing credentials for roles: {existing_roles}")
        return

    print("🔧 Setting up sample role credentials...")

    # Create sample admin credential
    admin_credential = RoleCredential(
        id="http://example.org/credentials/admin/123",
        issuer="did:example:issuer",
        issuanceDate="2025-08-01T12:00:00Z",
        expirationDate="2026-08-01T12:00:00Z",  # Valid for 1 year
        credentialSubject=CredentialSubject(id=f"did:example:{AGENT_ID}", role="admin"),
        # Note: In production, this would have a cryptographic proof
    )

    # Create sample manager credential
    manager_credential = RoleCredential(
        id="http://example.org/credentials/manager/456",
        issuer="did:example:issuer",
        issuanceDate="2025-08-01T12:00:00Z",
        expirationDate="2026-08-01T12:00:00Z",
        credentialSubject=CredentialSubject(
            id=f"did:example:{AGENT_ID}", role="manager"
        ),
    )

    # Add credentials to store
    await credential_store.add_credential(admin_credential)
    await credential_store.add_credential(manager_credential)

    print("✅ Sample credentials created: admin, manager")


async def setup_role_handlers():
    """Set up handlers for role credential requests."""
    # Note: In a full A2A implementation, this would register with the A2A client
    # For this demo, we'll handle requests through HTTP endpoints
    print("🔗 Role credential handlers configured")


# FastAPI Integration
auth = None


@app.on_event("startup")
async def startup_event():
    """Initialize the agent on startup."""
    global auth
    await setup_agent()
    auth = FastAPIPhlowAuth(middleware)


# A2A Protocol Endpoints


@app.get("/.well-known/agent.json")
async def agent_card():
    """Return agent card for A2A discovery."""
    return {
        "name": AGENT_NAME,
        "description": "A demo agent showcasing RBAC with Verifiable Credentials",
        "url": "http://localhost:8000",
        "skills": [
            {
                "name": "role-based-access",
                "description": "Demonstrates role-based access control",
            }
        ],
        "security_schemes": {
            "phlow-jwt": {"type": "http", "scheme": "bearer", "bearerFormat": "JWT"}
        },
        "metadata": {"agent_id": AGENT_ID},
    }


@app.post("/tasks/send")
async def handle_task(request: dict):
    """Handle A2A task requests, including role credential requests."""
    global credential_store

    message_type = request.get("type")

    if message_type == "role-credential-request":
        return await handle_role_credential_request(request)

    # Handle other task types
    return {
        "type": "task-response",
        "status": "completed",
        "result": f"Received task of type: {message_type}",
    }


async def handle_role_credential_request(request: dict) -> dict:
    """Handle role credential requests."""
    global credential_store

    try:
        # Parse the request
        role_request = RoleCredentialRequest(**request)

        # Check if we have the requested role
        if not await credential_store.has_role(role_request.required_role):
            return RoleCredentialResponse(
                nonce=role_request.nonce,
                error=f"Role '{role_request.required_role}' not available",
            ).dict()

        # Create verifiable presentation
        presentation = await credential_store.create_presentation(
            role=role_request.required_role,
            holder_did=f"did:example:{AGENT_ID}",
            challenge=role_request.challenge,
        )

        if not presentation:
            return RoleCredentialResponse(
                nonce=role_request.nonce,
                error=f"Failed to create presentation for role '{role_request.required_role}'",
            ).dict()

        # Return successful response
        return RoleCredentialResponse(
            nonce=role_request.nonce, presentation=presentation
        ).dict(by_alias=True)

    except Exception as e:
        return RoleCredentialResponse(
            nonce=request.get("nonce", "unknown"),
            error=f"Error processing role credential request: {str(e)}",
        ).dict()


# Protected Endpoints with Role Requirements


@app.get("/public")
async def public_endpoint():
    """Public endpoint - no authentication required."""
    return {
        "message": "This is a public endpoint",
        "timestamp": "2025-08-01T12:00:00Z",
        "agent": AGENT_NAME,
    }


@app.get("/basic-auth")
async def basic_auth_endpoint(
    context: PhlowContext = Depends(auth.create_auth_dependency()),
):
    """Basic authenticated endpoint - standard Phlow auth."""
    return {
        "message": "Basic authentication successful",
        "agent_id": context.agent.metadata.get("agent_id"),
        "agent_name": context.agent.name,
    }


@app.get("/admin-only")
async def admin_only_endpoint(
    context: PhlowContext = Depends(auth.create_role_auth_dependency("admin")),
):
    """Admin-only endpoint - requires admin role credential."""
    return {
        "message": "Admin access granted!",
        "agent_id": context.agent.metadata.get("agent_id"),
        "verified_roles": context.verified_roles,
        "admin_features": ["user-management", "system-configuration", "audit-logs"],
    }


@app.get("/manager-only")
async def manager_only_endpoint(
    context: PhlowContext = Depends(auth.create_role_auth_dependency("manager")),
):
    """Manager-only endpoint - requires manager role credential."""
    return {
        "message": "Manager access granted!",
        "agent_id": context.agent.metadata.get("agent_id"),
        "verified_roles": context.verified_roles,
        "manager_features": [
            "team-management",
            "project-oversight",
            "resource-allocation",
        ],
    }


@app.post("/secure-operation")
async def secure_operation(
    operation: dict,
    context: PhlowContext = Depends(auth.create_role_auth_dependency("admin")),
):
    """Secure operation requiring admin role."""
    return {
        "message": "Secure operation completed",
        "operation": operation.get("type", "unknown"),
        "executed_by": context.agent.metadata.get("agent_id"),
        "verified_roles": context.verified_roles,
        "timestamp": "2025-08-01T12:00:00Z",
    }


# Credential Management Endpoints


@app.get("/roles")
async def list_available_roles():
    """List all available roles for this agent."""
    global credential_store
    roles = await credential_store.get_all_roles()
    return {"agent_id": AGENT_ID, "available_roles": roles, "count": len(roles)}


@app.get("/roles/{role}")
async def get_role_info(role: str):
    """Get information about a specific role."""
    global credential_store

    if not await credential_store.has_role(role):
        raise HTTPException(status_code=404, detail=f"Role '{role}' not found")

    credential = await credential_store.get_credential(role)
    return {
        "role": role,
        "available": True,
        "issuer": credential.issuer,
        "issued_at": credential.issuance_date,
        "expires_at": credential.expiration_date,
    }


# Health and Status


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "agent": AGENT_NAME,
        "rbac_enabled": True,
        "timestamp": "2025-08-01T12:00:00Z",
    }


@app.get("/status")
async def status():
    """Detailed status information."""
    global credential_store

    roles = await credential_store.get_all_roles()

    return {
        "agent_id": AGENT_ID,
        "agent_name": AGENT_NAME,
        "status": "running",
        "rbac_status": {
            "enabled": True,
            "available_roles": roles,
            "role_count": len(roles),
        },
        "endpoints": {
            "public": "/public",
            "basic_auth": "/basic-auth",
            "admin_only": "/admin-only",
            "manager_only": "/manager-only",
            "role_info": "/roles",
            "a2a_discovery": "/.well-known/agent.json",
            "a2a_tasks": "/tasks/send",
        },
    }


if __name__ == "__main__":
    print("🚀 Starting Phlow RBAC Demo Agent...")
    print("📖 Check the README for setup instructions")
    print("🌐 Agent will be available at: http://localhost:8000")
    print("📋 API docs at: http://localhost:8000/docs")

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True, log_level="info")
