#!/bin/bash
# Bash script to stop BaseX and Redis services for dictionary application

echo -e "\033[33mStopping dictionary services (BaseX and Redis)...\033[0m"

# Stop BaseX Docker container
echo -e "\033[36mStopping BaseX container...\033[0m"
if docker ps -q --filter "name=basex" | grep -q .; then
    docker stop basex
    docker rm basex
    echo -e "\033[32m✓ BaseX container stopped and removed\033[0m"
else
    echo -e "\033[90mBaseX container not running\033[0m"
fi

# Stop Redis Docker container
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
echo -e "\n\033[36mVerifying services are stopped...\033[0m"

# Check BaseX
if docker ps -q --filter "name=basex" | grep -q .; then
    echo -e "\033[33m⚠ BaseX container still running\033[0m"
else
    echo -e "\033[32m✓ BaseX stopped\033[0m"
fi

# Check Redis
if docker ps -q --filter "name=redis" | grep -q .; then
    echo -e "\033[33m⚠ Redis container still running\033[0m"
else
    echo -e "\033[32m✓ Redis stopped\033[0m"
fi

# Check BaseX port
if nc -z localhost 1984 2>/dev/null; then
    echo -e "\033[33m⚠ BaseX port 1984 still in use\033[0m"
else
    echo -e "\033[32m✓ BaseX port free\033[0m"
fi

echo -e "\n\033[32mAll services stopped successfully!\033[0m"
