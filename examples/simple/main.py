"""
Simple A2A Agent Example

A complete A2A Protocol compliant agent with Gemini AI integration.
Based on the working E2E tests structure.
"""

import os
import uuid

import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI

# Load environment variables from .env file
load_dotenv()

app = FastAPI(title="Phlow Simple A2A Agent")


# A2A Agent Card Discovery (required by A2A protocol)
@app.get("/.well-known/agent.json")
def agent_card():
    """A2A Agent Card for discovery - required by A2A protocol"""
    return {
        "id": "phlow-simple-agent-001",
        "name": "Phlow Simple Agent",
        "description": "A simple A2A-compliant agent powered by Phlow framework",
        "version": "1.0.0",
        "author": "Phlow Framework",
        "capabilities": {
            "text_generation": True,
            "gemini_integration": True,
            "simple_responses": True,
        },
        "input_modes": ["text"],
        "output_modes": ["text"],
        "endpoints": {"task": "/tasks/send"},
        "metadata": {"framework": "phlow", "model": "gemini-2.5-flash-lite"},
    }


# A2A Task endpoint (required by A2A protocol)
@app.post("/tasks/send")
def send_task(task: dict):
    """A2A Task endpoint - handles incoming tasks from other agents"""
    try:
        # Extract message from A2A task format
        task_id = task.get("id", str(uuid.uuid4()))
        message = task.get("message", {})
        user_text = ""

        # Parse A2A message format
        if "parts" in message:
            for part in message["parts"]:
                if part.get("type") == "text":
                    user_text += part.get("text", "")
        else:
            user_text = message.get("text", "Hello from A2A")

        print(f"🤖 Simple Agent processing: '{user_text}'")

        # Use Gemini API for response (if available)
        if os.environ.get("GEMINI_API_KEY"):
            try:
                from google import genai

                client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
                response = client.models.generate_content(
                    model="gemini-2.5-flash-lite",
                    contents=f"You are a helpful Phlow A2A agent. Respond briefly and helpfully to: {user_text}",
                )
                response_text = response.text
            except Exception as e:
                response_text = f"I'm a Phlow A2A agent. You said: {user_text}. (Gemini unavailable: {e})"
        else:
            # Fallback response without Gemini
            response_text = (
                f"Hello! I'm a simple Phlow A2A agent. You said: {user_text}"
            )

        # Return A2A-compliant task response
        return {
            "id": task_id,
            "status": {"state": "completed", "message": "Task completed successfully"},
            "messages": [
                {"role": "agent", "parts": [{"type": "text", "text": response_text}]}
            ],
            "artifacts": [],
            "metadata": {
                "agent_id": "phlow-simple-agent-001",
                "model": "gemini-2.5-flash-lite",
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
                        {"type": "text", "text": f"Error processing request: {str(e)}"}
                    ],
                }
            ],
            "artifacts": [],
            "metadata": {"agent_id": "phlow-simple-agent-001", "error": str(e)},
        }


# Legacy endpoints for backwards compatibility
@app.get("/health")
def health():
    return {"status": "healthy", "agent_id": "phlow-simple-agent-001"}


@app.get("/info")
def info():
    return {
        "agent_id": "phlow-simple-agent-001",
        "name": "Phlow Simple Agent",
        "description": "A2A-compliant agent powered by Phlow framework",
        "a2a_compliant": True,
        "capabilities": ["text_generation", "simple_responses", "a2a_protocol"],
    }


if __name__ == "__main__":
    print("🚀 Starting Phlow Simple A2A Agent...")
    print("📋 A2A Agent Card: http://localhost:8000/.well-known/agent.json")
    print("🎯 A2A Task Endpoint: http://localhost:8000/tasks/send")
    print("💚 Health Check: http://localhost:8000/health")

    uvicorn.run(app, host="0.0.0.0", port=8000)
