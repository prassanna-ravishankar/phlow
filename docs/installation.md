# Installation

Choose your platform and follow the installation guide.

## JavaScript/TypeScript

### npm
```bash
npm install phlow-auth
```

### yarn
```bash
yarn add phlow-auth
```

### pnpm
```bash
pnpm add phlow-auth
```

### TypeScript Support
TypeScript definitions are included. No additional `@types` package needed.

## Python

### pip
```bash
pip install phlow-auth
```

### Poetry
```bash
poetry add phlow-auth
```

### Requirements File
```txt
phlow-auth>=0.1.0
```

### Python Version Support
- Python 3.8+
- Async/await support included
- Type hints included

## CLI Tools

The Phlow CLI helps with development tasks.

### Global Installation
```bash
npm install -g phlow-cli
```

### Project Installation
```bash
npm install --save-dev phlow-cli
```

### Verify Installation
```bash
phlow --version
```

## Supabase Setup

Phlow requires a Supabase project for agent registry and audit logs.

1. **Create a Supabase Project**
   - Go to [supabase.com](https://supabase.com)
   - Create a new project
   - Note your project URL and anon key

2. **Run Database Migrations**
   ```bash
   phlow init --supabase-url YOUR_URL --supabase-key YOUR_KEY
   ```

3. **Verify Setup**
   ```bash
   phlow test-connection
   ```

## Next Steps

- [Configuration](configuration.md) - Set up your agent
- [Quick Start](quickstart.md) - Build your first agent
- [Environment Variables](configuration.md#environment-variables) - Configure Phlow