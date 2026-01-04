#!/usr/bin/env bash
#
# Download BaseX JAR from basex.org
#
set -e

BASEX_VERSION="12.0"
BASEX_URL="https://basex.org/wp-content/uploads/${BASEX_VERSION}/BaseX_${BASEX_VERSION}.zip"
INSTALL_DIR="$(cd "$(dirname "$0")/../basex" && pwd)"
DEST_FILE="$INSTALL_DIR/BaseX.jar"
DEST_DIR="$INSTALL_DIR/lib"

echo "Downloading BaseX ${BASEX_VERSION}..."

# Check if already downloaded
if [ -f "$DEST_FILE" ]; then
    echo "BaseX.jar already exists at $DEST_FILE"
    echo "Remove it to re-download."
    exit 0
fi

# Create lib directory if needed
mkdir -p "$DEST_DIR"

# Download and extract
TEMP_DIR=$(mktemp -d)
trap "rm -rf $TEMP_DIR" EXIT

cd "$TEMP_DIR"
wget -q "$BASEX_URL" -O basex.zip
unzip -q basex.zip

# Find the JAR file
JAR=$(find . -name "BaseX*.jar" -type f | head -1)
if [ -z "$JAR" ]; then
    echo "ERROR: Could not find BaseX JAR in download"
    exit 1
fi

# Copy JAR and libs
cp "$JAR" "$DEST_FILE"
cp lib/*.jar "$DEST_DIR/" 2>/dev/null || true

echo "BaseX installed to $DEST_FILE"
echo "Libraries installed to $DEST_DIR"
