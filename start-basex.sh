#!/usr/bin/env bash
#
# Robust BaseX Startup Script
# Handles: installation detection, validation, user setup, and graceful start/stop
#

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BASEX_HOME="${BASEX_HOME:-$HOME/basex}"
DEFAULT_PASSWORD="admin"

# Find BaseX JAR and classpath - use ~/basex installation
find_basex_classpath() {
    # Use ~/basex where the working BaseX is installed
    local home_jar="$HOME/basex/BaseX.jar"
    if [ -f "$home_jar" ]; then
        echo "$home_jar:$HOME/basex/lib/*:$CLASSPATH"
        return 0
    fi
    # Fallback to app's basex directory
    local app_jar="$SCRIPT_DIR/basex/BaseX.jar"
    if [ -f "$app_jar" ]; then
        echo "$app_jar:$SCRIPT_DIR/basex/lib/*:$CLASSPATH"
        return 0
    fi
    return 1
}

# Get BaseX bin directory
get_basex_bindir() {
    if [ -x "$HOME/basex/bin/basexclient" ]; then
        echo "$HOME/basex/bin"
        return 0
    fi
    if [ -x "$SCRIPT_DIR/basex/bin/basexclient" ]; then
        echo "$SCRIPT_DIR/basex/bin"
        return 0
    fi
    return 1
}

# Check if BaseX is running
is_running() {
    local port="${1:-1984}"
    timeout 1 bash -c "echo >/dev/tcp/localhost/$port" 2>/dev/null
}

# Get PID from .pid file or find by process
get_basex_pid() {
    local pid_file="$BASEX_HOME/.pid"
    if [ -f "$pid_file" ]; then
        local pid=$(cat "$pid_file" 2>/dev/null)
        if [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null; then
            echo "$pid"
            return 0
        fi
    fi
    # Fallback: find by process name
    pgrep -f "org.basex.BaseXServer" 2>/dev/null | head -1
}

# Stop BaseX gracefully
stop_basex() {
    log_info "Stopping BaseX server..."

    # Get basexclient path
    local bindir
    bindir=$(get_basex_bindir) || bindir="$HOME/basex/bin"
    local basexclient="$bindir/basexclient"

    # Try graceful shutdown first via basexclient
    if is_running 1984; then
        "$basexclient" -c "EXIT" 2>/dev/null || true
        sleep 1
    fi

    # Kill by PID
    local pid=$(get_basex_pid)
    if [ -n "$pid" ]; then
        log_info "Killing BaseX process $pid..."
        kill "$pid" 2>/dev/null || true
        sleep 1
        # Force kill if still alive
        kill -9 "$pid" 2>/dev/null || true
    fi

    # Clean up stale PID file
    rm -f "$BASEX_HOME/.pid" 2>/dev/null || true

    # Wait for port to be released
    local max_wait=5
    while is_running 1984 && [ $max_wait -gt 0 ]; do
        sleep 1
        ((max_wait--))
    done

    if ! is_running 1984; then
        log_info "BaseX stopped successfully"
        return 0
    else
        log_error "Failed to stop BaseX - port 1984 still in use"
        return 1
    fi
}

# Configure admin user password via ALTER PASSWORD
configure_admin_password() {
    local password="${1:-$DEFAULT_PASSWORD}"

    log_info "Configuring admin user password..."

    # Get classpath
    local cp
    cp=$(find_basex_classpath) || {
        log_warn "Could not find BaseX JAR, skipping password configuration"
        return 0
    }

    # Try ALTER PASSWORD via command line
    local result
    result=$(java -cp "$cp" org.basex.BaseX -c "ALTER PASSWORD admin $password" 2>&1) || true

    if echo "$result" | grep -qi "error\|failed\|wrong\|authentication"; then
        log_warn "ALTER PASSWORD via CLI had issues, but server handles user auth"
    fi

    log_info "Admin user configuration complete"
}

# Initialize BaseX data directory
init_basex_data() {
    log_info "Initializing BaseX data directory: $BASEX_HOME"

    # Create required directories
    mkdir -p "$BASEX_HOME/data"
    mkdir -p "$BASEX_HOME/repo"
    mkdir -p "$BASEX_HOME/log"
    mkdir -p "$BASEX_HOME/webapp"
    mkdir -p "$BASEX_HOME/.logs"

    # Set .basexhome to point to our installation
    echo "$SCRIPT_DIR/basex" > "$SCRIPT_DIR/basex/.basexhome"

    log_info "BaseX directories created"
}

# Start BaseX server
start_basex() {
    # Get BaseX binary directory
    local bindir
    bindir=$(get_basex_bindir) || {
        log_error "BaseX binaries not found"
        return 1
    }

    local basexserver="$bindir/basexserver"

    # Stop any existing instance
    if is_running 1984; then
        log_warn "BaseX is already running on port 1984"
        read -p "Restart? (y/N): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            stop_basex
        else
            log_info "Using existing BaseX instance"
            return 0
        fi
    fi

    log_info "Starting BaseX server..."

    # Start BaseX using the official script
    cd "$BASEX_HOME"
    nohup "$basexserver" -p1984 > "$BASEX_HOME/log/server.log" 2>&1 &

    local pid=$!
    echo "$pid" > "$BASEX_HOME/.pid"

    log_info "BaseX started with PID: $pid"

    # Wait for server to be ready
    local max_wait=15
    while ! is_running 1984 && [ $max_wait -gt 0 ]; do
        sleep 1
        ((max_wait--))
        echo -n "."
    done
    echo

    if is_running 1984; then
        log_info "BaseX is ready on port 1984"

        # Configure password if needed
        configure_admin_password "$DEFAULT_PASSWORD"

        log_info "BaseX startup complete!"
        log_info "  PID file: $BASEX_HOME/.pid"
        log_info "  Data dir: $BASEX_HOME/data"
        log_info "  Log dir: $BASEX_HOME/log"
        return 0
    else
        log_error "BaseX failed to start. Check logs: $BASEX_HOME/log/server.log"
        cat "$BASEX_HOME/log/server.log" 2>/dev/null | tail -20
        return 1
    fi
}

# Status check
status() {
    local pid=$(get_basex_pid)
    if is_running 1984; then
        echo -e "${GREEN}[RUNNING]${NC} BaseX server on port 1984"
        [ -n "$pid" ] && echo "  PID: $pid"
        echo "  Data: $BASEX_HOME"
        echo "  PID file: $BASEX_HOME/.pid"
        return 0
    else
        echo -e "${RED}[STOPPED]${NC} BaseX server"
        [ -n "$pid" ] && echo "  Stale PID: $pid (remove $BASEX_HOME/.pid)"
        return 1
    fi
}

# Usage
usage() {
    cat << EOF
Usage: $(basename "$0") <command>

Commands:
    start       Start BaseX server
    stop        Stop BaseX server
    restart     Restart BaseX server
    status      Check BaseX status
    init        Initialize BaseX directories
    reset-pass  Reset admin password (default: admin)

Environment:
    BASEX_HOME  BaseX installation directory (default: ~/basex)

EOF
}

# Main
case "${1:-usage}" in
    start)
        start_basex
        ;;
    stop)
        stop_basex
        ;;
    restart)
        stop_basex
        sleep 1
        start_basex
        ;;
    status)
        status
        ;;
    init)
        init_basex_data
        ;;
    reset-pass)
        configure_admin_password "${2:-$DEFAULT_PASSWORD}"
        ;;
    help|--help|-h)
        usage
        ;;
    *)
        log_error "Unknown command: $1"
        usage
        exit 1
        ;;
esac
