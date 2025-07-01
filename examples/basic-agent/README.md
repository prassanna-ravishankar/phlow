# Basic Phlow Agent Example

This example demonstrates a simple Phlow agent with Supabase integration, showcasing agent-to-agent authentication.

## Features

- ✅ JWT-based authentication
- ✅ Permission-based access control
- ✅ Rate limiting
- ✅ Audit logging
- ✅ Token refresh handling
- ✅ Error handling

## Setup

1. **Install dependencies**:
   ```bash
   npm install
   ```

2. **Set up Supabase**:
   - Create a new Supabase project
   - Run the SQL schema from `../../packages/phlow-cli/src/utils/templates.ts`
   - Get your project URL and anon key

3. **Configure environment**:
   ```bash
   cp .env.example .env
   # Edit .env with your Supabase credentials and agent details
   ```

4. **Generate agent keys** (if not done already):
   ```bash
   # Using phlow CLI
   phlow init
   phlow generate-card
   ```

## Running the Agent

```bash
# Development mode (with auto-reload)
npm run dev

# Production mode
npm start
```

The agent will be available at `http://localhost:3000`

## API Endpoints

### Public Endpoints

- `GET /` - Agent information and available endpoints
- `GET /health` - Health check

### Protected Endpoints

- `GET /protected` - Basic authentication required
- `GET /data` - Requires `read:data` permission
- `POST /data` - Requires `write:data` permission  
- `GET /admin` - Requires `admin:users` permission

## Testing

Run the included test suite:

```bash
npm test
```

This will test:
- Health check
- Public endpoints
- Authentication (with and without tokens)
- Permission-based access control

## Authentication Flow

1. **Client agent** generates a JWT token signed with their private key
2. **Token includes**:
   - Agent ID (issuer)
   - Target agent ID (audience)
   - Permissions
   - Expiration time

3. **Basic agent** verifies the token using the client's public key
4. **Access granted** based on token validity and permissions

## Example Usage

### Generate a test token:

```bash
# Using phlow CLI
phlow test-token --target basic-agent-001

# Using curl
curl -H "Authorization: Bearer <token>" \
     -H "X-Phlow-Agent-Id: <your-agent-id>" \
     http://localhost:3000/protected
```

### Example client code:

```javascript
const { generateToken } = require('phlow-auth');

const token = generateToken(
  clientAgentCard,
  clientPrivateKey,
  'basic-agent-001',
  '1h'
);

const response = await fetch('http://localhost:3000/protected', {
  headers: {
    'Authorization': `Bearer ${token}`,
    'X-Phlow-Agent-Id': 'your-agent-id',
  },
});
```

## Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `SUPABASE_URL` | Your Supabase project URL | Yes |
| `SUPABASE_ANON_KEY` | Your Supabase anon key | Yes |
| `AGENT_ID` | Unique identifier for this agent | Yes |
| `AGENT_NAME` | Human-readable agent name | Yes |
| `AGENT_DESCRIPTION` | Agent description | No |
| `AGENT_PERMISSIONS` | Comma-separated permissions | No |
| `AGENT_PUBLIC_KEY` | RSA public key (PEM format) | Yes |
| `AGENT_PRIVATE_KEY` | RSA private key (PEM format) | Yes |
| `PORT` | Server port | No (default: 3000) |

## Security Notes

- 🔒 Keep your private key secure and never commit it to version control
- 🔄 Tokens have configurable expiration times
- 🚫 Failed authentication attempts are logged
- ⚡ Rate limiting prevents abuse
- 📊 All authentication events are audited

## Troubleshooting

### Common Issues

1. **"Missing required environment variable"**
   - Ensure all required variables are set in your `.env` file

2. **"Agent not found"**
   - Make sure the agent card is registered in Supabase
   - Check that the agent ID matches

3. **"Invalid token"**
   - Verify the token is properly signed
   - Check that the public/private key pair matches
   - Ensure the token hasn't expired

4. **"Insufficient permissions"**
   - Check that the requesting agent has the required permissions
   - Verify the permissions in the agent card

### Debug Mode

Set `DEBUG=phlow:*` to enable debug logging:

```bash
DEBUG=phlow:* npm start
```