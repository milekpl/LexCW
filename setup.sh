#!/usr/bin/env bash
# Main setup script for Lexicographic Curation Workbench
#
# Usage:
#   ./setup.sh              # Interactive mode (Docker mode)
#   ./setup.sh --hybrid     # Interactive mode (hybrid mode)
#   ./setup.sh --seed       # With minimal test data
#   ANSWER_YES=1 ./setup.sh # Non-interactive mode (for CI/CD)
#
# Exit codes:
#   0 - Success
#   1 - Prerequisite missing
#   2 - Configuration error
#   3 - Service startup failed

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="$SCRIPT_DIR/.env"
ENV_EXAMPLE="$SCRIPT_DIR/.env.example"

# Configuration
HYBRID_MODE=false
SEED_DATA=false
ANSWER_YES="${ANSWER_YES:-}"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Parse arguments
for arg in "$@"; do
    case $arg in
        --hybrid)
            HYBRID_MODE=true
            ;;
        --seed)
            SEED_DATA=true
            ;;
        --help|-h)
            echo "Lexicographic Curation Workbench - Setup Script"
            echo ""
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --hybrid    Use hybrid mode (local BaseX, Docker PostgreSQL/Redis)"
            echo "  --seed      Import minimal test data"
            echo "  --help      Show this help message"
            echo ""
            echo "Environment variables:"
            echo "  ANSWER_YES=1   Skip prompts (for CI/CD)"
            echo ""
            echo "For more information, see INSTALL.md"
            exit 0
            ;;
    esac
done

echo -e "${BLUE}=== Lexicographic Curation Workbench Setup ===${NC}"
echo ""

# --- Helper Functions ---

print_status() {
    echo -e "${GREEN}✓${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

print_step() {
    echo -e "${BLUE}→${NC} $1"
}

prompt_yes_no() {
    local question="$1"
    local default="${2:-n}"

    if [ -n "$ANSWER_YES" ]; then
        echo -e "${YELLOW}Auto-answering: ${default}${NC}"
        return 0
    fi

    echo -n "$question [$default]: "
    read -r answer

    if [ -z "$answer" ]; then
        answer="$default"
    fi

    [[ "$answer" =~ ^[Yy] ]]
}

# --- Prerequisite Checks ---

print_step "Checking prerequisites..."

# Check Docker
if ! command -v docker &> /dev/null; then
    print_error "Docker is not installed"
    echo "  Install Docker from: https://docs.docker.com/get-docker/"
    exit 1
fi
print_status "Docker found: $(docker --version)"

# Check Docker daemon
if ! docker info &>/dev/null; then
    print_error "Docker daemon is not running"
    echo "  Start Docker and try again"
    exit 1
fi
print_status "Docker daemon running"

# Check Docker Compose
if ! command -v docker-compose &> /dev/null && ! docker compose version &>/dev/null; then
    print_error "Docker Compose is not installed"
    exit 1
fi
print_status "Docker Compose found"

# Check Python
if ! command -v python3 &> /dev/null; then
    print_error "Python 3 is not installed"
    exit 1
fi
print_status "Python found: $(python3 --version)"

# Check Git
if ! command -v git &> /dev/null; then
    print_warning "Git not found (optional)"
else
    print_status "Git found: $(git --version)"
fi

echo ""

# --- Environment Setup ---

print_step "Setting up environment..."

# Create .env from .env.example if it doesn't exist
if [ ! -f "$ENV_FILE" ]; then
    if [ -f "$ENV_EXAMPLE" ]; then
        print_status "Creating .env from .env.example"
        cp "$ENV_EXAMPLE" "$ENV_FILE"
    else
        print_error ".env.example not found"
        exit 2
    fi
else
    print_status ".env already exists (skipping)"
fi

# Load environment
set -a
source "$ENV_FILE"
set +a

echo ""

# --- Python Virtual Environment ---

print_step "Setting up Python virtual environment..."

VENV_DIR="$SCRIPT_DIR/venv"

if [ ! -d "$VENV_DIR" ]; then
    print_status "Creating virtual environment"
    python3 -m venv "$VENV_DIR"
else
    print_status "Virtual environment already exists"
fi

# Activate and install dependencies
source "$VENV_DIR/bin/activate"

print_status "Upgrading pip"
pip install --quiet --upgrade pip 2>/dev/null || true

if [ -f "$SCRIPT_DIR/requirements.txt" ]; then
    print_status "Installing Python dependencies"
    pip install --quiet -r "$SCRIPT_DIR/requirements.txt" 2>/dev/null || {
        print_warning "Some packages may have failed to install"
    }
else
    print_warning "requirements.txt not found"
fi

print_status "Virtual environment ready"
echo ""

# --- Docker Services ---

print_step "Starting Docker services..."

if [ "$HYBRID_MODE" = true ]; then
    echo "  Mode: Hybrid (PostgreSQL + Redis via Docker, BaseX local)"
    docker-compose up -d postgres redis 2>/dev/null || {
        print_error "Failed to start PostgreSQL/Redis"
        exit 3
    }
else
    echo "  Mode: Docker (all services in containers)"
    docker-compose up -d 2>/dev/null || {
        print_error "Failed to start Docker services"
        exit 3
    }
fi

# Wait for services to be healthy
print_status "Waiting for services to start..."
sleep 3

echo ""

# --- Database Initialization ---

print_step "Initializing PostgreSQL database..."

# Run init-postgres.sh
if [ "$SEED_DATA" = true ]; then
    "$SCRIPT_DIR/scripts/init-postgres.sh" --seed
else
    "$SCRIPT_DIR/scripts/init-postgres.sh"
fi

echo ""

# --- BaseX Setup (Hybrid Mode) ---

if [ "$HYBRID_MODE" = true ]; then
    print_step "Setting up BaseX..."

    if [ ! -d "$SCRIPT_DIR/basex/bin" ]; then
        print_status "Downloading BaseX..."
        "$SCRIPT_DIR/scripts/download-basex.sh" || {
            print_warning "BaseX download failed (will use Docker BaseX instead)"
        }
    else
        print_status "BaseX already installed"
    fi

    # Start BaseX if not running
    if [ -f "$SCRIPT_DIR/basex/bin/status" ]; then
        if ! "$SCRIPT_DIR/basex/bin/status" &>/dev/null; then
            print_status "Starting BaseX server..."
            "$SCRIPT_DIR/basex/bin/start" 2>/dev/null || true
        else
            print_status "BaseX server already running"
        fi
    fi

    echo ""
fi

# --- Verification ---

print_step "Verifying setup..."

"$SCRIPT_DIR/scripts/verify-setup.sh" --quiet
VERIFY_RESULT=$?

if [ $VERIFY_RESULT -eq 0 ]; then
    print_status "All services verified"
else
    print_warning "Some services may not be running"
fi

echo ""
echo -e "${GREEN}=== Setup Complete! ===${NC}"
echo ""
echo "Next steps:"
echo "  1. Start the application: python run.py"
echo "  2. Open http://localhost:5000"
echo "  3. API docs at http://localhost:5000/apidocs"
echo ""
echo "Useful commands:"
echo "  ./scripts/verify-setup.sh   # Check service status"
echo "  docker-compose logs -f      # View logs"
echo "  docker-compose down         # Stop all services"

exit 0
