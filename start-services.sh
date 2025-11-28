#!/bin/bash
# Bash script to check/start services for dictionary application (WSL)
# BaseX runs on Windows host and is accessed via localhost
# Redis can run via Docker if needed

set -e

echo -e "\033[32mStarting dictionary services (BaseX and Redis)...\033[0m"

# Check/Start BaseX Server
echo -e "\033[36mChecking BaseX Server...\033[0m"

# Check if BaseX is already running
if nc -z localhost 1984 2>/dev/null || timeout 2 bash -c "</dev/tcp/localhost/1984" 2>/dev/null; then
    echo -e "\033[32m✓ BaseX Server is already running on port 1984\033[0m"
else
    # Start BaseX server in background
    echo -e "\033[36mStarting BaseX Server...\033[0m"
    
    # Get script directory
    SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
    
    # Initialize admin password if this is first time
    if [ ! -f "$HOME/basex/data/users.xml" ] || ! grep -q "admin" "$HOME/basex/data/users.xml" 2>/dev/null; then
        echo -e "\033[33mInitializing BaseX admin user...\033[0m"
        java -cp "$SCRIPT_DIR/BaseX120.jar" org.basex.BaseX -c "ALTER PASSWORD admin admin" > /dev/null 2>&1 || true
    fi
    
    # Start BaseX server as background process
    nohup "$SCRIPT_DIR/basexserver" > "$SCRIPT_DIR/basex.log" 2>&1 &
    BASEX_PID=$!
    
    # Save PID for later shutdown
    echo $BASEX_PID > "$SCRIPT_DIR/.basex.pid"
    
    # Wait for BaseX to be ready
    echo -e "\033[33mWaiting for BaseX to be ready...\033[0m"
    max_wait=30
    waited=0
    
    while [ $waited -lt $max_wait ]; do
        if nc -z localhost 1984 2>/dev/null || timeout 2 bash -c "</dev/tcp/localhost/1984" 2>/dev/null; then
            echo -e "\033[32m✓ BaseX Server is ready!\033[0m"
            break
        fi
        sleep 2
        waited=$((waited + 2))
    done
    
    if [ $waited -ge $max_wait ]; then
        echo -e "\033[31m✗ BaseX Server failed to start within ${max_wait}s\033[0m"
        echo -e "\033[37mCheck basex.log for details\033[0m"
        exit 1
    fi
fi

# Check BaseX HTTP interface (optional)
if nc -z localhost 8984 2>/dev/null || timeout 2 bash -c "</dev/tcp/localhost/8984" 2>/dev/null; then
    echo -e "\033[32m✓ BaseX HTTP interface accessible on port 8984\033[0m"
else
    echo -e "\033[33m⚠ BaseX HTTP interface not accessible (port 8984) - this is optional\033[0m"
fi

# Check/Start Redis
echo -e "\033[36mChecking Redis...\033[0m"

# First check if Redis is already running (Windows or WSL)
if nc -z localhost 6379 2>/dev/null || timeout 2 bash -c "</dev/tcp/localhost/6379" 2>/dev/null; then
    echo -e "\033[32m✓ Redis is already running on port 6379\033[0m"
else
    # Try to start Redis via Docker if available
    if docker version &> /dev/null; then
        # Check if redis container exists
        if docker ps -a --format '{{.Names}}' | grep -q "^redis$"; then
            echo -e "\033[36mStarting existing Redis container...\033[0m"
            docker start redis
        else
            echo -e "\033[36mStarting Redis (Docker)...\033[0m"
            docker run -d --name redis -p 6379:6379 redis:8
        fi
        
        # Wait for Redis to be ready
        echo -e "\033[33mWaiting for Redis to be ready...\033[0m"
        max_wait=30
        waited=0
        
        while [ $waited -lt $max_wait ]; do
            if docker exec redis redis-cli ping 2>/dev/null | grep -q "PONG"; then
                echo -e "\033[32m✓ Redis is ready!\033[0m"
                break
            fi
            sleep 2
            waited=$((waited + 2))
        done
        
        if [ $waited -ge $max_wait ]; then
            echo -e "\033[33mWarning: Redis may not be fully ready yet.\033[0m"
        fi
    else
        echo -e "\033[33m⚠ Redis not running and Docker not available\033[0m"
        echo -e "\033[37mThe application can work without Redis (caching will be disabled)\033[0m"
    fi
fi

echo -e "\n\033[32m✓ All services are ready!\033[0m"

# Check if BaseX database is empty and offer to initialize
if command -v python3 &> /dev/null || [ -f "$SCRIPT_DIR/.venv/bin/python" ]; then
    PYTHON="${SCRIPT_DIR}/.venv/bin/python"
    [ ! -f "$PYTHON" ] && PYTHON="python3"
    
    ENTRY_COUNT=$($PYTHON -c "
import sys
sys.path.insert(0, '$SCRIPT_DIR')
try:
    from app.database.basex_connector import BaseXConnector
    from app.services.dictionary_service import DictionaryService
    connector = BaseXConnector('localhost', 1984, 'admin', 'admin', 'dictionary')
    connector.connect()
    dict_service = DictionaryService(connector)
    _, count = dict_service.list_entries(limit=1)
    print(count)
    connector.disconnect()
except:
    print('0')
" 2>/dev/null || echo "0")
    
    if [ "$ENTRY_COUNT" = "0" ]; then
        echo -e "\n\033[33m⚠  BaseX database is empty\033[0m"
        echo -e "\033[37mWould you like to initialize it with sample data? (y/N)\033[0m"
        read -p "> " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            "$SCRIPT_DIR/init-basex-data.sh"
        fi
    else
        echo -e "\n\033[36mDatabase contains $ENTRY_COUNT entries\033[0m"
    fi
fi

echo -e "\n\033[36mService URLs:\033[0m"
echo -e "\033[37m- BaseX Web Interface: http://localhost:8984/dba\033[0m"
echo -e "\033[37m- BaseX Client Port: 1984\033[0m"
echo -e "\033[37m- Redis Port: 6379\033[0m"

echo -e "\n\033[36mNotes:\033[0m"
echo -e "\033[37m- BaseX is running locally in WSL (check basex.log for logs)\033[0m"
echo -e "\033[37m- To stop services: ./stop-services.sh\033[0m"
echo -e "\033[37m- To stop Redis only: docker stop redis\033[0m"
