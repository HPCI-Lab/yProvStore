#!/bin/bash

# Move to the directory of this script
cd "$(dirname "$0")"

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

# Install the required packages
uv pip install src/cli/

# Export the PYTHONPATH
export PYTHONPATH="${PWD}/src/cli/"
