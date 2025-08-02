# Phlow Scripts

Utility scripts for Phlow development and validation.

## validate-examples.sh

Comprehensive validation script for examples that tests with real dependencies.

### What it tests:

#### CI-Safe Validation (no external dependencies):
- File structure (README.md, main.py, requirements.txt)
- Python syntax validation
- Dependency resolution check
- Import testing
- A2A Protocol endpoint presence
- Agent card structure validation
- Task endpoint response structure

#### Full Local Validation (with external dependencies):
- All CI-safe tests plus:
- Real dependency installation in isolated environments
- Live server startup testing
- HTTP endpoint testing
- Integration with external APIs (if configured)

### Usage:

```bash
# Run comprehensive validation (requires API keys for full testing)
uv run task validate-examples

# Or run directly
bash scripts/validate-examples.sh
```

### Requirements:

- `uv` package manager
- Python 3.11+
- Optional: API keys for external services (Gemini, etc.)
- Optional: Docker for E2E tests

### Example Output:

```
ℹ️  Starting comprehensive examples validation...
ℹ️  📂 Validating Simple Agent example (full mode)...
✅ Required files present
ℹ️  Creating isolated environment...
ℹ️  Installing dependencies...
✅ Dependencies installed
✅ Python syntax valid
ℹ️  Testing imports...
✅ Imports successful
ℹ️  Testing A2A Protocol compliance...
✅ Agent card validation passed
✅ Task endpoint validation passed
📝 Response preview: Hello! I'm a simple Phlow A2A agent. You said: Hel...
✅ A2A Protocol compliance verified
ℹ️  Testing server startup...
✅ Live agent card endpoint working
✅ Live health endpoint working
✅ Live task endpoint working
✅ Server startup test passed
✅ Simple Agent example validation complete!
```

### CI Integration:

The GitHub Actions workflow runs a subset of these tests that don't require external dependencies:
- File structure validation
- Syntax checking
- Import testing
- A2A Protocol compliance
- Mock endpoint testing

For full validation with real APIs and Docker, run the script locally.

## Adding New Validation

To add validation for new examples:

1. Ensure your example follows the standard structure:
   ```
   examples/your-example/
   ├── README.md
   ├── main.py
   └── requirements.txt
   ```

2. The script will automatically detect and validate it

3. Make sure your example:
   - Has A2A Protocol endpoints (`/.well-known/agent.json`, `/tasks/send`)
   - Gracefully handles missing API keys
   - Can run without external dependencies for basic testing
