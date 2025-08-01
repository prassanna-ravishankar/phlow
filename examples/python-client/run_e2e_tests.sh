#!/bin/bash

# End-to-End Test Runner for Phlow Agent
# This script starts the Docker Compose stack, runs E2E tests, and cleans up

set -e

echo "🧪 Phlow E2E Test Runner"
echo "========================"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if we're in the right directory
if [[ ! -f "docker-compose.yml" ]]; then
    print_error "Please run this script from the examples/python-client directory"
    exit 1
fi

# Check if Docker is running
if ! docker info >/dev/null 2>&1; then
    print_error "Docker is not running. Please start Docker and try again."
    exit 1
fi

# Check if uv is available
if ! command -v uv &> /dev/null; then
    print_error "uv is not installed. Please install it first: pip install uv"
    exit 1
fi

# Function to cleanup on exit
cleanup() {
    if [[ "${CLEANUP_ON_EXIT:-true}" == "true" ]]; then
        print_status "Cleaning up Docker containers..."
        docker-compose down --volumes --remove-orphans >/dev/null 2>&1 || true
        print_success "Cleanup complete"
    else
        print_warning "Skipping cleanup (containers still running)"
    fi
}

# Set trap for cleanup
trap cleanup EXIT

# Parse command line arguments
CLEANUP_ON_EXIT=true
RUN_SLOW_TESTS=false
VERBOSE=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --no-cleanup)
            CLEANUP_ON_EXIT=false
            shift
            ;;
        --slow)
            RUN_SLOW_TESTS=true
            shift
            ;;
        --verbose|-v)
            VERBOSE=true
            shift
            ;;
        --help|-h)
            echo "Usage: $0 [options]"
            echo "Options:"
            echo "  --no-cleanup    Don't stop containers after tests"
            echo "  --slow          Include slow/performance tests"
            echo "  --verbose,-v    Verbose output"
            echo "  --help,-h       Show this help"
            exit 0
            ;;
        *)
            print_error "Unknown option: $1"
            exit 1
            ;;
    esac
done

print_status "Starting Docker Compose stack..."

# Start the stack
if [[ "$VERBOSE" == "true" ]]; then
    docker-compose up -d
else
    docker-compose up -d >/dev/null 2>&1
fi

# Wait for services to be healthy
print_status "Waiting for services to start..."

# Function to check if a service is healthy
check_service() {
    local url=$1
    local timeout=${2:-30}
    local elapsed=0
    
    while [[ $elapsed -lt $timeout ]]; do
        if curl -s --connect-timeout 2 "$url" >/dev/null 2>&1; then
            return 0
        fi
        sleep 2
        elapsed=$((elapsed + 2))
    done
    return 1
}

# Check each service
services=(
    "http://localhost:54321:Supabase API"
    "http://localhost:54323:Supabase Studio"
    "http://localhost:8000/health:Phlow Agent"
)

all_healthy=true
for service in "${services[@]}"; do
    url="${service%:*}"
    name="${service#*:}"
    
    print_status "Checking $name..."
    if check_service "$url" 60; then
        print_success "$name is healthy"
    else
        print_error "$name failed to start"
        all_healthy=false
    fi
done

if [[ "$all_healthy" != "true" ]]; then
    print_error "Some services failed to start. Check logs with: docker-compose logs"
    exit 1
fi

# Install test dependencies
print_status "Installing test dependencies..."
if [[ "$VERBOSE" == "true" ]]; then
    uv pip install -e ".[examples]" pytest requests
else
    uv pip install -e ".[examples]" pytest requests >/dev/null 2>&1
fi

# Run the tests
print_status "Running E2E tests..."

pytest_args=("-v" "test_e2e.py")

if [[ "$RUN_SLOW_TESTS" == "true" ]]; then
    print_status "Including slow/performance tests..."
else
    pytest_args+=("-m" "not slow")
fi

if [[ "$VERBOSE" == "true" ]]; then
    pytest_args+=("-s" "--tb=short")
else
    pytest_args+=("--tb=line")
fi

# Run tests
if uv run pytest "${pytest_args[@]}"; then
    print_success "All E2E tests passed! 🎉"
    
    # Show service URLs
    echo ""
    echo "🌐 Service URLs (while containers are running):"
    echo "   📊 Supabase Studio: http://localhost:54323"
    echo "   🌐 Supabase API: http://localhost:54321"
    echo "   🐍 Phlow Agent: http://localhost:8000"
    echo "   📖 Agent Docs: http://localhost:8000/docs"
    
    if [[ "$CLEANUP_ON_EXIT" == "false" ]]; then
        echo ""
        echo "💡 Containers are still running for manual testing"
        echo "   Stop with: docker-compose down"
    fi
    
    exit 0
else
    print_error "Some tests failed"
    
    if [[ "$VERBOSE" != "true" ]]; then
        echo ""
        print_status "For more details, run with --verbose flag"
        print_status "Or check service logs: docker-compose logs [service-name]"
    fi
    
    exit 1
fi