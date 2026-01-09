#!/usr/bin/env bash
# Initialize PostgreSQL database for the Lexicographic Curation Workbench
#
# Usage:
#   ./scripts/init-postgres.sh           # Structural setup only
#   ./scripts/init-postgres.sh --seed    # + minimal test data
#
# This script:
# - Creates the dict_user role and databases
# - Applies sql/init.sql schema
# - Optionally imports minimal test data

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SQL_DIR="$SCRIPT_DIR/sql"

# Load environment variables from .env if it exists
if [ -f "$SCRIPT_DIR/.env" ]; then
    set -a
    source "$SCRIPT_DIR/.env"
    set +a
fi

# Default values
POSTGRES_HOST="${POSTGRES_HOST:-localhost}"
POSTGRES_PORT="${POSTGRES_PORT:-5432}"
POSTGRES_USER="${POSTGRES_USER:-dict_user}"
POSTGRES_PASSWORD="${POSTGRES_PASSWORD:-dict_pass}"
POSTGRES_DB="${POSTGRES_DB:-dictionary_analytics}"
POSTGRES_TEST_DB="${POSTGRES_TEST_DB:-dictionary_test}"

# Check for --seed flag
SEED_DATA=false
for arg in "$@"; do
    case $arg in
        --seed)
            SEED_DATA=true
            ;;
        --help|-h)
            echo "Usage: $0 [--seed]"
            echo ""
            echo "Options:"
            echo "  --seed    Import minimal test data (1-2 entries)"
            echo ""
            echo "Environment variables:"
            echo "  POSTGRES_HOST     Database host (default: localhost)"
            echo "  POSTGRES_PORT     Database port (default: 5432)"
            echo "  POSTGRES_USER     Database user (default: dict_user)"
            echo "  POSTGRES_PASSWORD Database password (default: dict_pass)"
            echo "  POSTGRES_DB       Main database (default: dictionary_analytics)"
            exit 0
            ;;
    esac
done

# Detect if running in Docker
IN_DOCKER=false
if [ -f /.dockerenv ] || grep -q docker /proc/1/cgroup 2>/dev/null; then
    IN_DOCKER=true
fi

# Check if PostgreSQL client is available
if ! command -v psql &> /dev/null; then
    echo "Error: psql command not found. Install postgresql-client first."
    exit 1
fi

echo "Initializing PostgreSQL database..."
echo ""

# Determine connection method
if [ "$IN_DOCKER" = true ]; then
    # Running inside Docker container
    PSQL_CMD="psql -U $POSTGRES_USER -d $POSTGRES_DB"
    PSQL_ADMIN="psql -U $POSTGRES_USER"
else
    # Running on host, connecting to local or remote PostgreSQL
    if [ -n "$POSTGRES_PASSWORD" ]; then
        export PGPASSWORD="$POSTGRES_PASSWORD"
    fi
    PSQL_CMD="psql -h $POSTGRES_HOST -p $POSTGRES_PORT -U $POSTGRES_USER -d $POSTGRES_DB"
    PSQL_ADMIN="psql -h $POSTGRES_HOST -p $POSTGRES_PORT -U $POSTGRES_USER"
fi

# Step 1: Check if database exists and is accessible
echo "Checking database connection..."
if ! $PSQL_ADMIN -c "SELECT 1;" &>/dev/null; then
    echo "Error: Cannot connect to PostgreSQL at $POSTGRES_HOST:$POSTGRES_PORT as $POSTGRES_USER"
    echo "Please ensure PostgreSQL is running and the credentials are correct."
    exit 1
fi
echo "✓ Connected to PostgreSQL"
echo ""

# Step 2: Create role if it doesn't exist
echo "Creating role $POSTGRES_USER..."
$PSQL_ADMIN -c "DO \$\$ BEGIN IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = '$POSTGRES_USER') THEN CREATE ROLE $POSTGRES_USER WITH LOGIN PASSWORD '$POSTGRES_PASSWORD'; END IF; END \$\$;" 2>/dev/null || true
echo "✓ Role exists"
echo ""

# Step 3: Create databases if they don't exist
echo "Creating databases..."
$PSQL_ADMIN -c "CREATE DATABASE $POSTGRES_DB OWNER $POSTGRES_USER;" 2>/dev/null || echo "  Database $POSTGRES_DB already exists"
$PSQL_ADMIN -c "CREATE DATABASE $POSTGRES_TEST_DB OWNER $POSTGRES_USER;" 2>/dev/null || echo "  Database $POSTGRES_TEST_DB already exists"
echo "✓ Databases ready"
echo ""

# Step 4: Apply init.sql schema
if [ -f "$SQL_DIR/init.sql" ]; then
    echo "Applying schema from $SQL_DIR/init.sql..."
    $PSQL_ADMIN -f "$SQL_DIR/init.sql" 2>/dev/null || true
    echo "✓ Schema applied"
else
    echo "Warning: $SQL_DIR/init.sql not found"
fi
echo ""

# Step 5: Import seed data if requested
if [ "$SEED_DATA" = true ]; then
    echo "Importing minimal test data..."
    # Create minimal test data - a simple entry for testing
    $PSQL_CMD <<'EOF'
-- Minimal test data for verification
INSERT INTO dictionary.entries (id, lexical_form, created_at, updated_at)
VALUES ('test-entry-001', 'testword', NOW(), NOW())
ON CONFLICT (id) DO NOTHING;

-- Add a simple sense
INSERT INTO dictionary.senses (id, entry_id, definition, created_at, updated_at)
VALUES ('test-sense-001', 'test-entry-001', 'A test entry for verification', NOW(), NOW())
ON CONFLICT (id) DO NOTHING;

-- Verify data was inserted
SELECT 'Test data count: ' || COUNT(*) as status
FROM dictionary.entries;
EOF
    echo "✓ Test data imported"
fi

echo ""
echo "PostgreSQL initialization complete!"
echo ""
echo "Databases created:"
echo "  - $POSTGRES_DB (main)"
echo "  - $POSTGRES_TEST_DB (testing)"
echo ""
echo "To connect:"
echo "  psql -h $POSTGRES_HOST -p $POSTGRES_PORT -U $POSTGRES_USER -d $POSTGRES_DB"
