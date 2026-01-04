#!/usr/bin/env bash
#
# Test BaseX installation
#
set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
NC='\033[0m' # No Color

die() {
    echo -e "${RED}ERROR: $1${NC}" >&2
    exit 1
}

pass() {
    echo -e "${GREEN}PASS: $1${NC}"
}

BASEX_JAR="basex/BaseX.jar"

echo "Testing BaseX setup..."

# Test 1: Check if JAR exists
if [ ! -f "$BASEX_JAR" ]; then
    die "BaseX JAR not found at $BASEX_JAR. Run scripts/download-basex.sh first."
fi
pass "BaseX JAR exists"

# Test 2: Check Java
if ! command -v java &> /dev/null; then
    die "Java is not installed"
fi
JAVA_VER=$(java -version 2>&1 | head -1)
pass "Java installed ($JAVA_VER)"

# Test 3: JAR is valid
if ! java -cp "$BASEX_JAR" org.basex.BaseX -v &> /dev/null; then
    die "BaseX JAR is not valid"
fi
pass "BaseX JAR is valid"

# Test 4: Can start server briefly
echo "Testing BaseX server startup..."
if timeout 10 java -cp "$BASEX_JAR" org.basex.BaseXServer -d &> /dev/null; then
    pass "BaseX server can start"
    # Try to stop it
    java -cp "$BASEX_JAR" org.basex.BaseXServer -s &> /dev/null || true
else
    die "BaseX server failed to start"
fi

echo -e "\n${GREEN}All tests passed!${NC}"
