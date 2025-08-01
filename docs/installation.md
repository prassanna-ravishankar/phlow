# Installation

## Python Package

### pip
```bash
pip install phlow
```

### Poetry
```bash
poetry add phlow
```

### Requirements File
```txt
phlow>=0.1.0
```

### Python Version Support
- Python 3.10+
- Async/await support included
- Type hints included

## Supabase Setup

Phlow requires a Supabase project for agent registry and audit logs.

1. **Create a Supabase Project**
   - Go to [supabase.com](https://supabase.com)
   - Create a new project
   - Note your project URL and anon key

2. **Set up database schema**
   - Run the SQL migrations from `docs/database-schema.sql`

## Next Steps

- [Configuration](configuration.md) - Set up your agent
- [Quick Start](quickstart.md) - Build your first agent
- [Environment Variables](configuration.md#environment-variables) - Configure Phlow