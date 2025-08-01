"""
Python Agent Example using Phlow Authentication

This example demonstrates how to create a Python-based agent using FastAPI
and Phlow authentication middleware.
"""

import os
from datetime import datetime
from typing import Optional, Dict, Any

from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from dotenv import load_dotenv

from phlow import (
    PhlowMiddleware,
    PhlowConfig,
    AgentCard,
    PhlowContext,
    generate_token,
    AuthenticationError,
    AuthorizationError,
    RateLimitError,
)
from phlow.integrations.fastapi import create_phlow_dependency

# Load environment variables
load_dotenv()

# Validate required environment variables
required_env_vars = [
    "SUPABASE_URL",
    "SUPABASE_ANON_KEY", 
    "AGENT_ID",
    "AGENT_NAME",
    "AGENT_PUBLIC_KEY",
    "AGENT_PRIVATE_KEY"
]

for var in required_env_vars:
    if not os.getenv(var):
        raise ValueError(f"Missing required environment variable: {var}")

# Parse agent permissions
permissions = os.getenv("AGENT_PERMISSIONS", "read:data").split(",")
permissions = [p.strip() for p in permissions if p.strip()]

# Create agent card
agent_card = AgentCard(
    agent_id=os.getenv("AGENT_ID"),
    name=os.getenv("AGENT_NAME"),
    description=os.getenv("AGENT_DESCRIPTION", "Python Phlow agent example"),
    permissions=permissions,
    public_key=os.getenv("AGENT_PUBLIC_KEY").replace("\\n", "\n"),
    endpoints={
        "api": f"http://localhost:{os.getenv('PORT', '8000')}",
        "health": f"http://localhost:{os.getenv('PORT', '8000')}/health",
    },
    metadata={
        "language": "python",
        "framework": "fastapi",
        "version": "1.0.0",
        "environment": os.getenv("ENVIRONMENT", "development"),
    }
)

# Create Phlow configuration
config = PhlowConfig(
    supabase_url=os.getenv("SUPABASE_URL"),
    supabase_anon_key=os.getenv("SUPABASE_ANON_KEY"),
    agent_card=agent_card,
    private_key=os.getenv("AGENT_PRIVATE_KEY").replace("\\n", "\n"),
    enable_audit=True,
    rate_limiting={
        "max_requests": int(os.getenv("RATE_LIMIT_REQUESTS", "100")),
        "window_ms": int(os.getenv("RATE_LIMIT_WINDOW_MS", "60000")),
    }
)

# Initialize Phlow middleware
phlow = PhlowMiddleware(config)

# Create FastAPI app
app = FastAPI(
    title="Python Phlow Agent",
    description="Agent-to-Agent authentication example using Python and FastAPI",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create authentication dependencies
auth_required = create_phlow_dependency(phlow)
read_data_required = create_phlow_dependency(phlow, required_permissions=["read:data"])
write_data_required = create_phlow_dependency(phlow, required_permissions=["write:data"])
admin_required = create_phlow_dependency(phlow, required_permissions=["admin:users"])

# Global exception handler for Phlow errors
@app.exception_handler(AuthenticationError)
async def authentication_error_handler(request, exc):
    return HTTPException(
        status_code=401,
        detail={
            "error": "Authentication failed",
            "code": exc.code,
            "message": exc.message,
        }
    )

@app.exception_handler(AuthorizationError)
async def authorization_error_handler(request, exc):
    return HTTPException(
        status_code=403,
        detail={
            "error": "Authorization failed", 
            "code": exc.code,
            "message": exc.message,
        }
    )

@app.exception_handler(RateLimitError)
async def rate_limit_error_handler(request, exc):
    return HTTPException(
        status_code=429,
        detail={
            "error": "Rate limit exceeded",
            "code": exc.code,
            "message": exc.message,
        }
    )

# Routes

@app.get("/")
async def root():
    """Get agent information and available endpoints."""
    return {
        "message": "Python Phlow Agent",
        "agent": {
            "id": agent_card.agent_id,
            "name": agent_card.name,
            "description": agent_card.description,
            "permissions": agent_card.permissions,
            "metadata": agent_card.metadata,
        },
        "endpoints": {
            "health": "/health",
            "protected": "/protected",
            "data": "/data",
            "admin": "/admin",
            "agent_info": "/agent-info",
            "generate_token": "/generate-token",
        },
        "documentation": "/docs",
        "timestamp": datetime.utcnow().isoformat(),
    }

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "agent_id": agent_card.agent_id,
        "timestamp": datetime.utcnow().isoformat(),
        "version": "1.0.0",
    }

@app.get("/protected")
async def protected_endpoint(context: PhlowContext = Depends(auth_required)):
    """Basic protected endpoint requiring authentication."""
    return {
        "message": "Hello from Python protected endpoint!",
        "requesting_agent": {
            "id": context.agent.agent_id,
            "name": context.agent.name,
            "permissions": context.claims.permissions,
        },
        "timestamp": datetime.utcnow().isoformat(),
    }

@app.get("/data")
async def get_data(context: PhlowContext = Depends(read_data_required)):
    """Data endpoint requiring read:data permission."""
    mock_data = {
        "users": [
            {"id": 1, "name": "Alice", "email": "alice@example.com"},
            {"id": 2, "name": "Bob", "email": "bob@example.com"},
        ],
        "metrics": {
            "total_users": 2,
            "active_sessions": 5,
            "last_updated": datetime.utcnow().isoformat(),
        }
    }
    
    return {
        "message": "Data access granted",
        "data": mock_data,
        "accessed_by": context.agent.agent_id,
        "timestamp": datetime.utcnow().isoformat(),
    }

@app.post("/data")
async def create_data(
    data: Dict[str, Any],
    context: PhlowContext = Depends(write_data_required)
):
    """Data creation endpoint requiring write:data permission."""
    return {
        "message": "Data created successfully",
        "received_data": data,
        "created_by": context.agent.agent_id,
        "timestamp": datetime.utcnow().isoformat(),
    }

@app.get("/admin")
async def admin_endpoint(context: PhlowContext = Depends(admin_required)):
    """Admin endpoint requiring admin:users permission."""
    admin_data = {
        "system_status": "operational",
        "total_agents": 42,
        "active_connections": 15,
        "memory_usage": "2.1 GB",
        "cpu_usage": "45%",
        "uptime": "5 days, 12 hours",
    }
    
    return {
        "message": "Admin access granted",
        "admin_data": admin_data,
        "accessed_by": context.agent.agent_id,
        "timestamp": datetime.utcnow().isoformat(),
    }

@app.get("/agent-info")
async def get_agent_info(context: PhlowContext = Depends(auth_required)):
    """Get detailed information about the requesting agent."""
    return {
        "message": "Agent information retrieved",
        "agent": {
            "id": context.agent.agent_id,
            "name": context.agent.name,
            "description": context.agent.description,
            "permissions": context.agent.permissions,
            "endpoints": context.agent.endpoints,
            "metadata": context.agent.metadata,
        },
        "token_claims": {
            "subject": context.claims.sub,
            "issuer": context.claims.iss,
            "audience": context.claims.aud,
            "issued_at": datetime.fromtimestamp(context.claims.iat).isoformat(),
            "expires_at": datetime.fromtimestamp(context.claims.exp).isoformat(),
            "permissions": context.claims.permissions,
        },
        "timestamp": datetime.utcnow().isoformat(),
    }

@app.post("/generate-token")
async def generate_token_endpoint(
    request: Dict[str, str],
    context: PhlowContext = Depends(auth_required)
):
    """Generate a token for communicating with another agent."""
    target_agent_id = request.get("target_agent_id")
    expires_in = request.get("expires_in", "1h")
    
    if not target_agent_id:
        raise HTTPException(
            status_code=400,
            detail="target_agent_id is required"
        )
    
    try:
        token = generate_token(
            agent_card,
            config.private_key,
            target_agent_id,
            expires_in
        )
        
        return {
            "message": "Token generated successfully",
            "token": token,
            "target_agent_id": target_agent_id,
            "expires_in": expires_in,
            "generated_by": context.agent.agent_id,
            "timestamp": datetime.utcnow().isoformat(),
            "usage_example": {
                "curl": f'curl -H "Authorization: Bearer {token}" -H "X-Phlow-Agent-Id: {agent_card.agent_id}" http://target-agent/protected'
            }
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate token: {str(e)}"
        )

# Startup event
@app.on_event("startup")
async def startup_event():
    """Application startup tasks."""
    print(f"🚀 Python Phlow Agent starting up...")
    print(f"📋 Agent ID: {agent_card.agent_id}")
    print(f"👤 Agent Name: {agent_card.name}")
    print(f"🔐 Permissions: {', '.join(agent_card.permissions)}")
    print(f"🌐 Server will be available at: http://localhost:{os.getenv('PORT', '8000')}")
    print(f"📖 API Documentation: http://localhost:{os.getenv('PORT', '8000')}/docs")

if __name__ == "__main__":
    port = int(os.getenv("PORT", "8000"))
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=port,
        reload=True,
        log_level="info"
    )