#!/bin/bash
set -euo pipefail

# These env vars come from .env / container env: POSTGRES_USER, POSTGRES_DB, POSTGRES_PASSWORD
# Make sure they are set in .env
: "${POSTGRES_USER:?}"
: "${POSTGRES_DB:?}"
: "${POSTGRES_PASSWORD:?}"

# Run SQL with heredoc — shell expands variables
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-SQL
CREATE ROLE pgbouncer_user WITH LOGIN PASSWORD '${POSTGRES_PASSWORD}';
-- grant connect to the current DB name (expanded by shell above)
GRANT CONNECT ON DATABASE "${POSTGRES_DB}" TO pgbouncer_user;
GRANT USAGE ON SCHEMA public TO pgbouncer_user;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO pgbouncer_user;
SQL
