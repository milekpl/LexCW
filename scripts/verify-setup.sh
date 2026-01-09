#!/usr/bin/env bash
# Verify all services are running correctly
#
# Usage:
#   ./scripts/verify-setup.sh           # Full check with output
#   ./scripts/verify-setup.sh --quiet   # Exit code only
#   ./scripts/verify-setup.sh --docker  # Check Docker containers
#
# Exit codes:
#   0 - All critical services running
#   1 - One or more critical services down
#   2 - Verification failed

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
QUIET_MODE=false
DOCKER_MODE=false

# Parse arguments
for arg in "$@"; do
    case $arg in
        --quiet)
            QUIET_MODE=true
            ;;
        --docker)
            DOCKER_MODE=true
            ;;
        --help|-h)
            echo "Usage: $0 [--quiet] [--docker]"
            echo ""
            echo "Options:"
            echo "  --quiet   Exit code only, minimal output"
            echo "  --docker  Check Docker containers instead of local services"
            exit 0
            ;;
    esac
done

# Load environment
if [ -f "$SCRIPT_DIR/.env" ]; then
    set -a
    source "$SCRIPT_DIR/.env"
    set +a
fi

# Default values
POSTGRES_HOST="${POSTGRES_HOST:-localhost}"
POSTGRES_PORT="${POSTGRES_PORT:-5432}"
POSTGRES_TEST_PORT="${POSTGRES_TEST_PORT:-5433}"
BASEX_HOST="${BASEX_HOST:-localhost}"
BASEX_PORT="${BASEX_PORT:-1984}"
BASEX_HTTP_PORT="${BASEX_HTTP_PORT:-8984}"
REDIS_HOST="${REDIS_HOST:-localhost}"
REDIS_PORT="${REDIS_PORT:-6379}"
FLASK_PORT="${FLASK_PORT:-5000}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Track service status
SERVICES_RUNNING=0
SERVICES_TOTAL=0
SERVICES_DOWN=0

# Helper function to check TCP port
check_port() {
    local host=$1
    local port=$2
    local name=$3

    SERVICES_TOTAL=$((SERVICES_TOTAL + 1))

    if nc -z -w 3 "$host" "$port" 2>/dev/null; then
        [ "$QUIET_MODE" = false ] && echo -e "${GREEN}✓${NC} $name: Running (port $port)"
        SERVICES_RUNNING=$((SERVICES_RUNNING + 1))
        return 0
    else
        [ "$QUIET_MODE" = false ] && echo -e "${RED}✗${NC} $name: Not running (port $port)"
        SERVICES_DOWN=$((SERVICES_DOWN + 1))
        return 1
    fi
}

# Helper function to check HTTP endpoint
check_http() {
    local url=$1
    local name=$2
    local optional=${3:-false}

    SERVICES_TOTAL=$((SERVICES_TOTAL + 1))

    if curl -sf -o /dev/null -w "%{http_code}" "$url" 2>/dev/null | grep -q "200\|302"; then
        [ "$QUIET_MODE" = false ] && echo -e "${GREEN}✓${NC} $name: HTTP OK"
        SERVICES_RUNNING=$((SERVICES_RUNNING + 1))
        return 0
    else
        if [ "$optional" = true ]; then
            [ "$QUIET_MODE" = false ] && echo -e "${YELLOW}○${NC} $name: Not running (optional)"
        else
            [ "$QUIET_MODE" = false ] && echo -e "${RED}✗${NC} $name: Not responding (HTTP)"
        fi
        SERVICES_DOWN=$((SERVICES_DOWN + 1))
        return 1
    fi
}

# Helper function to check via docker exec
check_docker_service() {
    local container=$1
    local name=$2
    local check_cmd=$3

    SERVICES_TOTAL=$((SERVICES_TOTAL + 1))

    if docker exec "$container" sh -c "$check_cmd" &>/dev/null; then
        [ "$QUIET_MODE" = false ] && echo -e "${GREEN}✓${NC} $name: Running (Docker)"
        SERVICES_RUNNING=$((SERVICES_RUNNING + 1))
        return 0
    else
        [ "$QUIET_MODE" = false ] && echo -e "${RED}✗${NC} $name: Not running"
        SERVICES_DOWN=$((SERVICES_DOWN + 1))
        return 1
    fi
}

# Check if Docker is running
check_docker() {
    if ! docker info &>/dev/null; then
        [ "$QUIET_MODE" = false ] && echo -e "${RED}✗${NC} Docker: Not running"
        return 1
    fi
    [ "$QUIET_MODE" = false ] && echo -e "${GREEN}✓${NC} Docker: Running"
    return 0
}

if [ "$QUIET_MODE" = false ]; then
    echo "=== Service Health Check ==="
    echo ""
fi

if [ "$DOCKER_MODE" = true ]; then
    # Docker mode - check Docker and containers
    check_docker || true

    check_docker_service "dictionary_postgres" "PostgreSQL (main)" "pg_isready -U dict_user -d dictionary_analytics"
    check_docker_service "dictionary_postgres_test" "PostgreSQL (test)" "pg_isready -U dict_user -d dictionary_test"
    check_docker_service "dictionary_basex" "BaseX Server" "echo 'test' | nc localhost 1984" || true
    check_docker_service "dictionary_redis" "Redis" "redis-cli ping"
else
    # Local mode - check TCP ports directly
    check_port "$POSTGRES_HOST" "$POSTGRES_PORT" "PostgreSQL (dictionary_analytics)"
    check_port "$POSTGRES_HOST" "$POSTGRES_TEST_PORT" "PostgreSQL (dictionary_test)"
    check_port "$BASEX_HOST" "$BASEX_PORT" "BaseX Server"
    check_http "http://$BASEX_HOST:$BASEX_HTTP_PORT/" "BaseX HTTP" "optional"
    check_port "$REDIS_HOST" "$REDIS_PORT" "Redis"

    # Check Flask app (only if we can connect to DBs)
    if [ $SERVICES_DOWN -eq 0 ]; then
        SERVICES_TOTAL=$((SERVICES_TOTAL + 1))
        if curl -sf -o /dev/null -w "%{http_code}" "http://localhost:$FLASK_PORT/health" 2>/dev/null | grep -q "200"; then
            [ "$QUIET_MODE" = false ] && echo -e "${GREEN}✓${NC} Flask App: Running (port $FLASK_PORT)"
            SERVICES_RUNNING=$((SERVICES_RUNNING + 1))
        else
            [ "$QUIET_MODE" = false ] && echo -e "${BLUE}?${NC} Flask App: Not started (run 'python run.py')"
        fi
    fi
fi

if [ "$QUIET_MODE" = false ]; then
    echo ""
    echo "=== Summary ==="
    echo "$SERVICES_RUNNING/$SERVICES_TOTAL services running"

    if [ $SERVICES_DOWN -gt 0 ]; then
        echo ""
        echo -e "${YELLOW}To start services:${NC}"
        echo "  Docker mode:  docker-compose up -d"
        echo "  Hybrid mode:  docker-compose up -d postgres redis && ./start-services.sh"
    fi
fi

# Return exit code based on service status
if [ $SERVICES_DOWN -gt 0 ]; then
    exit 1
fi
exit 0
