# Minimal A2A + Supabase Example

This example demonstrates how Phlow extends the A2A Protocol SDK with Supabase integration.

## What This Shows

1. **A2A Protocol Compliance** - Uses standard A2A agent card format
2. **Supabase Integration** - Adds audit logging, RLS, and agent registry
3. **Minimal Code** - Authentication in just a few lines

## Key Benefits

- ✅ Full A2A Protocol compatibility (via official SDK)
- ✅ Automatic audit trail in Supabase
- ✅ Rate limiting out of the box
- ✅ Row Level Security helpers
- ✅ Centralized agent registry

## Running the Example

```bash
# Set environment variables
export PRIVATE_KEY="your-private-key"
export PUBLIC_KEY="your-public-key"
export SUPABASE_URL="https://your-project.supabase.co"
export SUPABASE_ANON_KEY="your-anon-key"

# Install and run
npm install phlow-auth express
node index.js
```

## Architecture

```
Your Agent (A2A SDK + Phlow)
    ↓
A2A Protocol Authentication
    ↓
Phlow Middleware Layer
    ↓
Supabase (Audit Logs, RLS, Registry)
```

Phlow doesn't replace A2A - it extends it with production-ready features!