#!/bin/bash
# Bash script to stop services for dictionary application (WSL)
# Note: BaseX runs on Windows host and should be stopped from Windows

echo -e "\033[36mStopping dictionary services...\033[0m"

# Stop BaseX Server
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PID_FILE="$SCRIPT_DIR/.basex.pid"

if [ -f "$PID_FILE" ]; then
    BASEX_PID=$(cat "$PID_FILE")
    if ps -p $BASEX_PID > /dev/null 2>&1; then
        echo -e "\033[36mStopping BaseX Server (PID: $BASEX_PID)...\033[0m"
        kill $BASEX_PID
        
        # Wait for graceful shutdown
        sleep 2
        
        # Force kill if still running
        if ps -p $BASEX_PID > /dev/null 2>&1; then
            echo -e "\033[33mForce stopping BaseX...\033[0m"
            kill -9 $BASEX_PID
        fi
        
        echo -e "\033[32m✓ BaseX Server stopped\033[0m"
    else
        echo -e "\033[33m⚠ BaseX Server (PID: $BASEX_PID) not running\033[0m"
    fi
    rm "$PID_FILE"
else
    echo -e "\033[33m⚠ No BaseX PID file found (may not be running)\033[0m"
fi


# Stop Redis Docker container (if running)
echo -e "\033[36mStopping Redis container...\033[0m"
if docker ps -q --filter "name=redis" | grep -q .; then
    docker stop redis
    docker rm redis
    echo -e "\033[32m✓ Redis container stopped and removed\033[0m"
else
    echo -e "\033[90mRedis container not running\033[0m"
fi

# Stop Flask/Python processes
echo -e "\033[36mStopping Flask/Python processes...\033[0m"
flask_pids=$(pgrep -f "flask|run.py|app.py" 2>/dev/null || true)
if [ -n "$flask_pids" ]; then
    echo "$flask_pids" | xargs kill -9 2>/dev/null || true
    echo -e "\033[32m✓ Flask/Python processes stopped\033[0m"
else
    echo -e "\033[90mNo Flask/Python processes found\033[0m"
fi

# Verify services are stopped
echo -e "\n\033[36mVerifying services...\033[0m"

# Check Redis
if docker ps -q --filter "name=redis" | grep -q .; then
    echo -e "\033[33m⚠ Redis container still running\033[0m"
else
    echo -e "\033[32m✓ Redis stopped\033[0m"
fi

# Check if BaseX is still accessible (runs on Windows)
if python3 -c "import socket; s=socket.socket(); s.settimeout(2); s.connect(('localhost', 1984)); s.close()" 2>/dev/null; then
    echo -e "\033[33m⚠ BaseX still running on Windows (port 1984)\033[0m"
    echo -e "\033[37m  To stop BaseX, stop it from Windows:\033[0m"
    echo -e "\033[37m  - Close BaseX server window, or\033[0m"
    echo -e "\033[37m  - Use stop-services.ps1 on Windows\033[0m"
else
    echo -e "\033[32m✓ BaseX not accessible\033[0m"
fi

echo -e "\n\033[32mWSL services stopped successfully!\033[0m"
