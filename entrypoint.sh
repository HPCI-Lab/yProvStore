#!/bin/sh

# Exit immediately if a command exits with a non-zero status.
set -e

# Navigate to the application directory (where alembic migrations are located)
cd /app

# Run alembic migrations
uv run alembic upgrade head

# Execute the command passed to this script
exec "$@"