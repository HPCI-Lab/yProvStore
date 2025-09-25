#!/bin/bash

# Save current directory and move to the directory of this script
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
pushd "$SCRIPT_DIR" > /dev/null || exit 1

# Check if 'uv' is installed
if ! command -v uv &> /dev/null; then
    pip install uv
fi

# Recreate venv only if needed
if [ ! -d ".venv" ]; then
  echo "Creating virtual environment..."
  uv venv .venv
else
  echo "Using existing virtual environment..."
fi

# Activate the virtual environment
source .venv/bin/activate

# Check if Node.js is installed
if ! command -v node &> /dev/null; then
    echo "Node.js is not installed. Please install Node.js from https://nodejs.org/ and re-run this script."
    popd > /dev/null || true
    exit 1
fi

# Install the required Python packages
uv pip install src/cli/

# Build the blockchain lib (install TypeScript and run the build)
if [ -d "src/cli/utils/blockchain/lib" ]; then
  cd src/cli/utils/blockchain/lib || true
  if [ -f package.json ]; then
    npm install typescript
    npm run build || true
  fi
fi

# Return to the original directory
popd > /dev/null || true

# Export the PYTHONPATH (pointing to the repo script directory)
export PYTHONPATH="${PYTHONPATH}:${SCRIPT_DIR}/src/cli/"
