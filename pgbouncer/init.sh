#!/bin/bash
set -e

# Check if required environment variables are set
if [ -z "$POSTGRES_USER" ] || [ -z "$POSTGRES_PASSWORD" ] || [ -z "$POSTGRES_DB" ]; then
    echo "Error: POSTGRES_USER, POSTGRES_PASSWORD, and POSTGRES_DB environment variables must be set"
    exit 1
fi

echo "=== Initializing pgbouncer configuration ==="

# Create pgbouncer directory if it doesn't exist
mkdir -p /pgbouncer

echo "1. Generating pgbouncer userlist for user: $POSTGRES_USER"

# Generate MD5 hash for pgbouncer authentication
# Format: md5 + md5(password + username)
password_user_hash=$(echo -n "${POSTGRES_PASSWORD}${POSTGRES_USER}" | md5sum | cut -d' ' -f1)
hashed_password="md5${password_user_hash}"

# Create userlist.txt with the user and hashed password
echo "\"$POSTGRES_USER\" \"$hashed_password\"" > /pgbouncer/configuration/userlist.txt

echo "   ✓ Generated userlist.txt successfully"

echo "2. Substituting environment variables in pgbouncer.ini..."

# Check if template exists
if [ ! -f "/pgbouncer/pgbouncer.ini.template" ]; then
    echo "Error: /pgbouncer/pgbouncer.ini.template not found"
    exit 1
fi

# Substitute environment variables in the template
sed -e "s/\${POSTGRES_DB}/${POSTGRES_DB}/g" \
    -e "s/\${POSTGRES_USER}/${POSTGRES_USER}/g" \
    -e "s/\${POSTGRES_PASSWORD}/${POSTGRES_PASSWORD}/g" \
    /pgbouncer/pgbouncer.ini.template > /pgbouncer/configuration/pgbouncer.ini

echo "   ✓ Generated pgbouncer.ini successfully"

echo "=== pgbouncer initialization completed ==="
echo "Generated files:"
echo "- userlist.txt:"
# cat /pgbouncer/configuration/userlist.txt
echo "- pgbouncer.ini (first 10 lines):"
# head -10 /pgbouncer/configuration/pgbouncer.ini