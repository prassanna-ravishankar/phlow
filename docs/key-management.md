# Key Management Guide

Phlow provides secure key management to protect your cryptographic keys. Instead of storing keys in environment variables (insecure), Phlow supports multiple secure storage backends.

## Overview

The key management system provides:
- Multiple storage backends (HashiCorp Vault, AWS Secrets Manager, encrypted files)
- Automatic key loading from secure storage
- Key rotation capabilities
- Backward compatibility with environment variables (development only)

## Storage Backends

### 1. Environment Variables (Development Only)

⚠️ **WARNING**: Only use for development/testing. Not secure for production.

```bash
export PHLOW_KEY_STORE_TYPE=environment
export PHLOW_PRIVATE_KEY_default="your-private-key"
export PHLOW_PUBLIC_KEY_default="your-public-key"
```

### 2. Encrypted File Store

Stores keys in an encrypted JSON file. Better than environment variables but still not ideal for production.

```bash
export PHLOW_KEY_STORE_TYPE=encrypted_file
export PHLOW_KEY_STORE_FILE=".phlow/keys.enc"
export PHLOW_MASTER_KEY="your-master-encryption-key"
```

### 3. HashiCorp Vault (Recommended for Production)

Provides enterprise-grade security with audit logging, access controls, and key rotation.

```bash
export PHLOW_KEY_STORE_TYPE=vault
export VAULT_URL="https://vault.example.com"
export VAULT_TOKEN="your-vault-token"
```

Setup Vault:
```bash
# Enable KV v2 secrets engine
vault secrets enable -path=phlow kv-v2

# Store a key pair
vault kv put phlow/keys/my-agent \
  private_key=@private_key.pem \
  public_key=@public_key.pem
```

### 4. AWS Secrets Manager

Ideal for AWS deployments with IAM-based access control.

```bash
export PHLOW_KEY_STORE_TYPE=aws
export AWS_REGION="us-east-1"
# AWS credentials via IAM role or environment
```

## Usage Examples

### Basic Usage

Keys are automatically loaded from secure storage:

```python
from phlow import PhlowConfig, PhlowMiddleware, AgentCard

config = PhlowConfig(
    agent_card=AgentCard(
        name="My Agent",
        description="Secure agent",
        service_url="https://my-agent.com",
        skills=["chat"],
        metadata={"agent_id": "my-agent"}
    ),
    # No need to provide keys - loaded from secure storage
    supabase_url="https://project.supabase.co",
    supabase_anon_key="anon-key"
)

middleware = PhlowMiddleware(config)
```

### Manual Key Management

```python
from phlow.security import KeyManager, HashiCorpVaultKeyStore

# Initialize key store
key_store = HashiCorpVaultKeyStore(
    vault_url="https://vault.example.com",
    vault_token="token"
)

# Create key manager
key_manager = KeyManager(key_store)

# Generate new key pair
private_key, public_key = key_manager.generate_key_pair("my-agent")

# Retrieve keys
private_key, public_key = key_manager.get_key_pair("my-agent")

# Rotate keys
new_private, new_public = key_manager.rotate_key_pair("my-agent")
```

### Custom Key Store

Implement the `KeyStore` interface for custom storage:

```python
from phlow.security import KeyStore

class CustomKeyStore(KeyStore):
    def get_private_key(self, key_id: str) -> Optional[str]:
        # Your implementation
        pass

    def get_public_key(self, key_id: str) -> Optional[str]:
        # Your implementation
        pass

    def store_key_pair(self, key_id: str, private_key: str, public_key: str) -> None:
        # Your implementation
        pass

    def delete_key_pair(self, key_id: str) -> None:
        # Your implementation
        pass
```

## Security Best Practices

1. **Never commit keys to version control**
2. **Use HashiCorp Vault or AWS Secrets Manager in production**
3. **Rotate keys regularly**
4. **Use different keys for different environments**
5. **Enable audit logging for key access**
6. **Restrict key access with IAM/policies**
7. **Use hardware security modules (HSM) for critical keys**

## Migration from Environment Variables

To migrate existing deployments:

1. Choose a secure key store (Vault or AWS)
2. Store your existing keys:
   ```python
   key_manager.store_key_pair("my-agent", existing_private, existing_public)
   ```
3. Update environment variables:
   ```bash
   export PHLOW_KEY_STORE_TYPE=vault
   export VAULT_URL="https://vault.example.com"
   export VAULT_TOKEN="token"
   ```
4. Remove old key environment variables
5. Restart your application

## Troubleshooting

### Key Not Found
- Verify the key ID matches your agent ID
- Check key store connectivity
- Ensure proper permissions (IAM/Vault policies)

### Permission Denied
- Verify Vault token or AWS credentials
- Check key store policies
- Ensure network connectivity

### Performance Issues
- Keys are cached after first retrieval
- Consider increasing cache TTL for stable keys
- Use local encrypted file store for edge deployments
