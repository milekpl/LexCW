#!/bin/bash
# Bash script to start BaseX and Redis services for dictionary application
# This script uses Docker for both BaseX and Redis

set -e

echo -e "\033[32mStarting dictionary services (BaseX and Redis)...\033[0m"

# Check if Docker is running
if ! docker version &> /dev/null; then
    echo -e "\033[31mError: Docker is not running. Please start Docker.\033[0m"
    exit 1
fi

# Start BaseX Server via Docker
echo -e "\033[36mStarting BaseX Server (Docker)...\033[0m"
docker run -d --name basex \
    -p 1984:1984 \
    -p 8984:8984 \
    -v "$(pwd)/data/basex":/srv/basex/data \
    basex/basexhttp:latest

# Wait for BaseX to be ready
echo -e "\033[33mWaiting for BaseX to be ready...\033[0m"
sleep 5

# Check if BaseX is running
if nc -z localhost 1984 2>/dev/null; then
    echo -e "\033[32m✓ BaseX Server started successfully on port 1984\033[0m"
else
    echo -e "\033[33mWarning: BaseX may still be starting up...\033[0m"
fi

# Start Redis via Docker
echo -e "\033[36mStarting Redis (Docker)...\033[0m"
docker run -d --name redis -p 6379:6379 redis:8

# Wait for Redis to be ready
echo -e "\033[33mWaiting for Redis to be ready...\033[0m"
max_wait=30
waited=0

while [ $waited -lt $max_wait ]; do
    if docker exec redis redis-cli ping 2>/dev/null | grep -q "PONG"; then
        echo -e "\033[32m✓ Redis is ready!\033[0m"
        break
    fi
    
    echo -e "\033[33mWaiting for Redis... (${waited}s)\033[0m"
    sleep 2
    waited=$((waited + 2))
done

if [ $waited -ge $max_wait ]; then
    echo -e "\033[33mWarning: Redis may not be fully ready yet.\033[0m"
fi

echo -e "\n\033[36mService Status:\033[0m"
docker ps --filter "name=basex" --filter "name=redis" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

echo -e "\n\033[36mService URLs:\033[0m"
echo -e "\033[37m- BaseX Web Interface: http://localhost:8984/dba\033[0m"
echo -e "\033[37m- BaseX Client Port: 1984\033[0m"
echo -e "\033[37m- Redis Port: 6379\033[0m"

echo -e "\n\033[33mTo stop services, run: ./stop-services.sh\033[0m"
