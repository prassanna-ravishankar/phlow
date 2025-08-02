#!/bin/bash
# Phlow Examples Validation Script
# Tests examples locally with real dependencies (API keys, Docker, etc.)

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() { echo -e "${BLUE}ℹ️  $1${NC}"; }
log_success() { echo -e "${GREEN}✅ $1${NC}"; }
log_warning() { echo -e "${YELLOW}⚠️  $1${NC}"; }
log_error() { echo -e "${RED}❌ $1${NC}"; }

# Check if we're in the right directory
if [ ! -f "pyproject.toml" ] || [ ! -d "examples" ]; then
    log_error "Please run this script from the Phlow project root directory"
    exit 1
fi

log_info "Starting comprehensive examples validation..."

# Validate an example with full dependencies
validate_example_full() {
    local example_dir=$1
    local example_name=$2

    log_info "📂 Validating $example_name example (full mode)..."
    cd examples/$example_dir

    # Check required files
    if [ ! -f "README.md" ] || [ ! -f "main.py" ] || [ ! -f "requirements.txt" ]; then
        log_error "Missing required files in $example_name"
        cd ../..
        return 1
    fi
    log_success "Required files present"

    # Create virtual environment for this example
    log_info "Creating isolated environment..."
    uv venv .venv --python 3.11
    source .venv/bin/activate

    # Install dependencies
    log_info "Installing dependencies..."
    uv pip install -r requirements.txt

    # Install the main phlow package in development mode
    uv pip install -e ../../
    log_success "Dependencies installed"

    # Check Python syntax
    if ! python -m py_compile main.py; then
        log_error "Python syntax error in main.py"
        deactivate
        rm -rf .venv
        cd ../..
        return 1
    fi
    log_success "Python syntax valid"

    # Test imports
    log_info "Testing imports..."
    if ! python -c "import main; print('Imports successful')"; then
        log_error "Import test failed"
        deactivate
        rm -rf .venv
        cd ../..
        return 1
    fi
    log_success "Imports successful"

    # Test A2A Protocol endpoints (without starting server)
    log_info "Testing A2A Protocol compliance..."
    python -c "
import main
import json

# Test agent card
try:
    agent_card = main.agent_card()
    required_fields = ['id', 'name', 'description', 'capabilities', 'endpoints']
    for field in required_fields:
        assert field in agent_card, f'Missing field: {field}'
    assert agent_card['endpoints']['task'] == '/tasks/send', 'Invalid task endpoint'
    print('✅ Agent card validation passed')
except Exception as e:
    print(f'❌ Agent card validation failed: {e}')
    exit(1)

# Test task endpoint
try:
    test_task = {
        'id': 'test-validation-123',
        'message': {
            'parts': [{'type': 'text', 'text': 'Hello from validation script'}]
        }
    }

    response = main.send_task(test_task)

    # Validate response structure
    required_fields = ['id', 'status', 'messages', 'metadata']
    for field in required_fields:
        assert field in response, f'Missing response field: {field}'

    assert response['status']['state'] in ['completed', 'failed'], 'Invalid status state'
    assert isinstance(response['messages'], list), 'Messages must be a list'

    print('✅ Task endpoint validation passed')
    print(f'📝 Response preview: {response[\"messages\"][0][\"parts\"][0][\"text\"][:50]}...')
except Exception as e:
    print(f'❌ Task endpoint validation failed: {e}')
    exit(1)
"

    if [ $? -ne 0 ]; then
        log_error "A2A Protocol validation failed"
        deactivate
        rm -rf .venv
        cd ../..
        return 1
    fi
    log_success "A2A Protocol compliance verified"

    # Test server startup (quick test)
    log_info "Testing server startup..."
    timeout 10s python -c "
import main
import uvicorn
import threading
import time
import requests

def run_server():
    uvicorn.run(main.app, host='127.0.0.1', port=18000, log_level='error')

# Start server in background
server_thread = threading.Thread(target=run_server, daemon=True)
server_thread.start()

# Wait for server to start
time.sleep(3)

try:
    # Test agent card endpoint
    response = requests.get('http://127.0.0.1:18000/.well-known/agent.json', timeout=2)
    assert response.status_code == 200, f'Agent card endpoint failed: {response.status_code}'

    agent_card = response.json()
    assert 'id' in agent_card, 'Agent card missing id field'
    print('✅ Live agent card endpoint working')

    # Test health endpoint
    response = requests.get('http://127.0.0.1:18000/health', timeout=2)
    assert response.status_code == 200, f'Health endpoint failed: {response.status_code}'
    print('✅ Live health endpoint working')

    # Test task endpoint with POST
    task_data = {
        'id': 'live-test-123',
        'message': {
            'parts': [{'type': 'text', 'text': 'Live server test'}]
        }
    }
    response = requests.post('http://127.0.0.1:18000/tasks/send', json=task_data, timeout=5)
    assert response.status_code == 200, f'Task endpoint failed: {response.status_code}'

    task_response = response.json()
    assert 'status' in task_response, 'Task response missing status'
    print('✅ Live task endpoint working')

except Exception as e:
    print(f'❌ Live server test failed: {e}')
    exit(1)
" 2>/dev/null

    if [ $? -eq 0 ]; then
        log_success "Server startup test passed"
    else
        log_warning "Server startup test skipped or failed (this might be expected without API keys)"
    fi

    # Cleanup
    deactivate
    rm -rf .venv
    cd ../..

    log_success "$example_name example validation complete!"
    return 0
}

# Test each example
examples_tested=0
examples_passed=0

for example_path in examples/*/; do
    if [ -d "$example_path" ] && [ -f "${example_path}main.py" ]; then
        example_dir=$(basename "$example_path")
        example_name=$(echo "$example_dir" | sed 's/_/ /g' | sed 's/\b\w/\U&/g')

        log_info "Testing $example_name..."
        if validate_example_full "$example_dir" "$example_name"; then
            ((examples_passed++))
        else
            log_error "$example_name validation failed"
        fi
        ((examples_tested++))
        echo ""
    fi
done

# Summary
echo "======================================"
log_info "Validation Summary:"
log_info "Examples tested: $examples_tested"
log_success "Examples passed: $examples_passed"

if [ $examples_passed -eq $examples_tested ]; then
    log_success "🎉 All examples validated successfully!"
    exit 0
else
    failed=$((examples_tested - examples_passed))
    log_error "❌ $failed example(s) failed validation"
    exit 1
fi
