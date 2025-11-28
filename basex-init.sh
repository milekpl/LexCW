#!/usr/bin/env bash

# Initialize BaseX with admin user
# This script creates the admin user if it doesn't exist

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Path to BaseX jar
BASEX_JAR="$SCRIPT_DIR/BaseX120.jar"

# Create admin user with default password
echo "Creating BaseX admin user..."
java -cp "$BASEX_JAR" org.basex.BaseX -c "CREATE USER admin admin" 2>&1 | grep -v "User.*already exists" || true
java -cp "$BASEX_JAR" org.basex.BaseX -c "GRANT admin TO admin" 2>&1 | grep -v "already" || true

# Optionally create the dictionary database
echo "Creating dictionary database..."
java -cp "$BASEX_JAR" org.basex.BaseX -c "CREATE DB dictionary" 2>&1 | grep -v "already exists" || true

echo "✓ BaseX initialization complete"
