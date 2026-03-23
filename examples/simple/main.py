"""
Simple A2A Agent Example

Demonstrates PhlowAuth with FastAPI — JWT authentication for A2A agents
without requiring Supabase. Optionally integrates Gemini for AI responses.
"""

import os
import uuid

import uvicorn
from dotenv import load_dotenv
from fastapi import Depends, FastAPI

from phlow import PhlowAuth

load_dotenv()

# --- Auth Setup ---
# PhlowAuth handles JWT creation and verification. No Supabase needed.
SECRET_KEY = os.getenv("AGENT_SECRET_KEY", "dev-secret-change-in-production")
auth = PhlowAuth(private_key=SECRET_KEY)
auth_required = auth.create_fastapi_dependency()

app = FastAPI(title="Phlow Simple A2A Agent")


# --- A2A Protocol Endpoints ---


@app.get("/.well-known/agent.json")
def agent_card():
    """A2A Agent Card for discovery."""
    return {
        "id": "phlow-simple-agent-001",
        "name": "Phlow Simple Agent",
        "description": "A2A-compliant agent with JWT auth powered by Phlow",
        "version": "1.0.0",
        "capabilities": {"text_generation": True},
        "input_modes": ["text"],
        "output_modes": ["text"],
        "endpoints": {"task": "/tasks/send"},
    }


@app.post("/tasks/send")
def send_task(task: dict, claims: dict = Depends(auth_required)):
    """A2A Task endpoint — requires JWT authentication."""
    task_id = task.get("id", str(uuid.uuid4()))
    agent_id = claims.get("sub", "anonymous")

    # Extract message from A2A task format
    message = task.get("message", {})
    user_text = ""
    if "parts" in message:
        for part in message["parts"]:
            if part.get("type") == "text":
                user_text += part.get("text", "")
    else:
        user_text = message.get("text", "Hello from A2A")

    # Generate response (with optional Gemini integration)
    if os.environ.get("GEMINI_API_KEY"):
        try:
            from google import genai

            client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
            response = client.models.generate_content(
                model="gemini-2.5-flash-lite",
                contents=f"You are a helpful A2A agent. Respond briefly to: {user_text}",
            )
            response_text = response.text
        except Exception as e:
            response_text = f"You said: {user_text}. (Gemini unavailable: {e})"
    else:
        response_text = f"Hello {agent_id}! You said: {user_text}"

    return {
        "id": task_id,
        "status": {"state": "completed"},
        "messages": [
            {"role": "agent", "parts": [{"type": "text", "text": response_text}]}
        ],
        "metadata": {"agent_id": "phlow-simple-agent-001"},
    }


@app.get("/health")
def health():
    return {"status": "healthy"}


# --- Generate a test token for trying the API ---


@app.post("/dev/token")
def generate_test_token():
    """Development-only: generate a test token for trying the API."""
    token = auth.create_token(agent_id="test-agent", name="Test Agent")
    return {"token": token, "usage": "Authorization: Bearer <token>"}


if __name__ == "__main__":
    print("Starting Phlow Simple A2A Agent...")
    print("Agent Card:     http://localhost:8000/.well-known/agent.json")
    print("Task Endpoint:  http://localhost:8000/tasks/send (requires JWT)")
    print("Test Token:     POST http://localhost:8000/dev/token")
    print("Health Check:   http://localhost:8000/health")

    uvicorn.run(app, host="0.0.0.0", port=8000)
