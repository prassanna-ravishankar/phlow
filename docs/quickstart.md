# Quick Start

Get a Phlow-protected agent running in 5 minutes.

## Install

=== "JavaScript"
    ```bash
    npm install phlow-auth
    ```

=== "Python"
    ```bash
    pip install phlow-auth
    ```

## Create Your Agent

=== "JavaScript"
    ```javascript
    import { PhlowMiddleware } from 'phlow-auth';
    import express from 'express';

    const app = express();

    // 1. Initialize Phlow
    const phlow = new PhlowMiddleware({
      agentCard: {
        name: 'My Agent',
        // A2A Protocol standard format
      },
      privateKey: process.env.PRIVATE_KEY,
      supabaseUrl: process.env.SUPABASE_URL,
      supabaseAnonKey: process.env.SUPABASE_ANON_KEY
    });

    // 2. Add authentication to any endpoint
    app.post('/api/chat', phlow.authenticate(), (req, res) => {
      res.json({ message: `Hello from ${req.phlow.agent.name}` });
    });

    app.listen(3000);
    ```

=== "Python"
    ```python
    from fastapi import FastAPI, Request
    from phlow import PhlowMiddleware

    app = FastAPI()

    # 1. Initialize Phlow
    phlow = PhlowMiddleware({
        'agent_card': {
            'name': 'My Agent',
            # A2A Protocol standard format
        },
        'private_key': os.getenv('PRIVATE_KEY'),
        'supabase_url': os.getenv('SUPABASE_URL'),
        'supabase_anon_key': os.getenv('SUPABASE_ANON_KEY')
    })

    # 2. Add authentication to any endpoint
    @app.post("/api/chat")
    @phlow.authenticate
    async def chat(request: Request):
        return {"message": f"Hello from {request.phlow.agent.name}"}
    ```

## Set Environment Variables

```bash
export PRIVATE_KEY="your-private-key"
export SUPABASE_URL="https://your-project.supabase.co"
export SUPABASE_ANON_KEY="your-anon-key"
```

## Run Your Agent

=== "JavaScript"
    ```bash
    node your-agent.js
    ```

=== "Python"
    ```bash
    uvicorn your_agent:app
    ```

## Test It

```bash
# Your agent is now A2A Protocol compliant!
curl http://localhost:3000/.well-known/agent.json
```

---

**Next Steps:**
- [Full Installation Guide](installation.md) - Platform-specific setup
- [Configuration Options](configuration.md) - All available settings
- [Making Agent Calls](guides/agent-calls.md) - Connect to other agents