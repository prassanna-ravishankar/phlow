#!/bin/bash
set -e

# E2E test runner with Docker auto-detection

if [ -S "$HOME/.rd/docker.sock" ]; then
  echo "✅ Rancher Desktop detected"
  export DOCKER_HOST="unix://$HOME/.rd/docker.sock"
else
  echo "✅ Using default Docker setup"
fi

# Run pytest with all arguments passed to this script
uv run pytest "$@"