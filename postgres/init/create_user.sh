#!/bin/bash
set -euo pipefail

# These env vars come from .env / container env: POSTGRES_USER, POSTGRES_DB, POSTGRES_PASSWORD
# Make sure they are set in .env
: "${POSTGRES_USER:?}"
: "${POSTGRES_DB:?}"
: "${POSTGRES_PASSWORD:?}"

# Run SQL with heredoc — shell expands variables
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-SQL
-- Update password for existing user
ALTER USER ${POSTGRES_USER} PASSWORD '${POSTGRES_PASSWORD}';
-- Ensure proper permissions
GRANT CONNECT ON DATABASE "${POSTGRES_DB}" TO ${POSTGRES_USER};
GRANT USAGE ON SCHEMA public TO ${POSTGRES_USER};
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO ${POSTGRES_USER};
GRANT SELECT, UPDATE ON ALL SEQUENCES IN SCHEMA public TO ${POSTGRES_USER};
SQL
