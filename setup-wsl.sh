#!/bin/bash
# Setup script for WSL development environment

set -e

echo "Setting up WSL development environment..."

# Update package list
echo "Updating package list..."
sudo apt-get update

# Install Python 3 and pip if not already installed
echo "Installing Python 3 and dependencies..."
sudo apt-get install -y python3 python3-pip python3-venv

# Install system dependencies for BaseX and other tools
echo "Installing system dependencies..."
sudo apt-get install -y \
    default-jre \
    git \
    curl \
    wget \
    build-essential

# Create virtual environment
echo "Creating Python virtual environment..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo "Virtual environment created"
else
    echo "Virtual environment already exists"
fi

# Activate virtual environment and install requirements
echo "Installing Python dependencies..."
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# Make scripts executable
echo "Making scripts executable..."
chmod +x start-services.sh stop-services.sh scripts/*.sh 2>/dev/null || true

# Check if BaseX is running
echo "Checking BaseX connection..."
if ! nc -z localhost 1984 2>/dev/null; then
    echo "⚠ BaseX server is not running on port 1984"
    echo "  Run './start-services.sh' to start services"
else
    echo "✓ BaseX server is running"
fi

echo ""
echo "✓ WSL development environment setup complete!"
echo ""
echo "Next steps:"
echo "  1. Activate virtual environment: source venv/bin/activate"
echo "  2. Start services: ./start-services.sh"
echo "  3. Run tests: python -m pytest tests/"
echo "  4. Start Flask app: python run.py"
echo ""
