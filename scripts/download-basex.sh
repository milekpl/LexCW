#!/usr/bin/env bash
# Download and install BaseX for local development (hybrid mode)
#
# Usage:
#   ./scripts/download-basex.sh           # Download latest BaseX
#   BASEX_VERSION=11.0 ./scripts/download-basex.sh  # Specific version
#
# Output:
#   basex/           - BaseX installation directory

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BASEX_DIR="$SCRIPT_DIR/basex"
BASEX_URL="${BASEX_URL:-https://files.basex.org/releases/BaseX-latest.zip}"
BASEX_VERSION="${BASEX_VERSION:-}"

echo "Downloading BaseX..."

# Check prerequisites
if ! command -v curl &> /dev/null && ! command -v wget &> /dev/null; then
    echo "Error: curl or wget is required"
    exit 1
fi

if ! command -v unzip &> /dev/null; then
    echo "Error: unzip is required"
    exit 1
fi

# Detect system architecture
OS="$(uname -s | tr '[:upper:]' '[:lower:]')"
ARCH="$(uname -m)"

case "$OS" in
    linux)
        case "$ARCH" in
            x86_64) DIST="x64" ;;
            aarch64|arm64) DIST="arm64" ;;
            *)
                echo "Error: Unsupported architecture: $ARCH"
                exit 1
                ;;
        esac
        ;;
    darwin)
        case "$ARCH" in
            x86_64) DIST="x64" ;;
            arm64) DIST="arm64" ;;
            *)
                echo "Error: Unsupported architecture: $ARCH"
                exit 1
                ;;
        esac
        ;;
    *)
        echo "Error: Unsupported operating system: $OS"
        exit 1
        ;;
esac

echo "Detected: $OS ($DIST)"

# Create temporary directory
TEMP_DIR=$(mktemp -d)
trap "rm -rf $TEMP_DIR" EXIT

BASEX_ZIP="$TEMP_DIR/basex.zip"
BASEX_EXTRACT="$TEMP_DIR/basex"

echo "Downloading from $BASEX_URL..."

# Download
if command -v curl &> /dev/null; then
    curl -fsSL -o "$BASEX_ZIP" "$BASEX_URL"
elif command -v wget &> /dev/null; then
    wget -q -O "$BASEX_ZIP" "$BASEX_URL"
fi

if [ ! -f "$BASEX_ZIP" ]; then
    echo "Error: Download failed"
    exit 1
fi

echo "Extracting..."

# Extract
unzip -q "$BASEX_ZIP" -d "$TEMP_DIR"

# Find the extracted directory
shopt -s nullglob
EXTRACTED_DIRS=("$TEMP_DIR"/*/)
shopt -u nullglob

if [ ${#EXTRACTED_DIRS[@]} -eq 0 ]; then
    # Try without trailing slash
    EXTRACTED_DIRS=("$TEMP_DIR"/*)
fi

if [ ${#EXTRACTED_DIRS[@]} -eq 0 ]; then
    echo "Error: Could not find extracted BaseX directory"
    exit 1
fi

# Get the first directory that looks like BaseX
for d in "$TEMP_DIR"/*; do
    if [ -d "$d" ] && [[ "$(basename "$d")" == BaseX* ]]; then
        EXTRACTED_DIR="$d"
        break
    fi
done

if [ -z "$EXTRACTED_DIR" ]; then
    # Just use the first directory
    EXTRACTED_DIR="${EXTRACTED_DIRS[0]}"
fi

echo "Installing from $EXTRACTED_DIR..."

# Backup existing installation if it exists
if [ -d "$BASEX_DIR" ]; then
    BACKUP_DIR="${BASEX_DIR}.backup.$(date +%Y%m%d%H%M%S)"
    echo "Backing up existing installation to $BACKUP_DIR"
    mv "$BASEX_DIR" "$BACKUP_DIR"
fi

# Move new installation
mkdir -p "$(dirname "$BASEX_DIR")"
mv "$EXTRACTED_DIR" "$BASEX_DIR"

# Make scripts executable
chmod +x "$BASEX_DIR/bin/"* 2>/dev/null || true

echo ""
echo "BaseX installed successfully!"
echo ""
echo "To start BaseX server:"
echo "  $BASEX_DIR/bin/start"
echo ""
echo "To stop BaseX server:"
echo "  $BASEX_DIR/bin/stop"
echo ""
echo "To access BaseX client:"
echo "  $BASEX_DIR/bin/basexclient"
echo ""

# Show version if available
if [ -f "$BASEX_DIR/bin/basex" ]; then
    VERSION=$("$BASEX_DIR/bin/basex" -v 2>&1 | head -1 || echo "unknown")
    echo "BaseX version: $VERSION"
fi
