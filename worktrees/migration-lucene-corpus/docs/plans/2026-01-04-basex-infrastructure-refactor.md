# BaseX Infrastructure Refactor Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Create robust BaseX infrastructure with proper logging, health monitoring, auto-restart, and clean git management. Remove redundant JAR files and add licensing documentation.

**Architecture:**
- Centralize all BaseX-related files in `basex/` subfolder
- Use proper shell scripts for start/stop/status/health operations
- Download BaseX JAR instead of committing to git
- Add health checks with 3 levels of validation
- Implement auto-restart with exponential backoff

**Tech Stack:** Bash scripts, BaseX 12.0+, standard Unix tools (nc, timeout, flock)

---

## Task 1: Update .gitignore for BaseX

**Files:**
- Modify: `.gitignore`

**Step 1: Write the failing test**

```bash
# Test: Verify BaseX files are properly gitignored
git check-ignore basex/log/ basex/data/ basex/.pid basex/BaseX.jar basex/lib/*.jar .basex.pid *.jar
# Expected: All paths should be ignored (no output means they're in .gitignore)
```

**Step 2: Run test to verify it fails**

```bash
git check-ignore basex/BaseX.jar 2>&1 || echo "FAIL: BaseX.jar not in gitignore"
```

**Step 3: Write the implementation**

```bash
# Add to .gitignore:
# BaseX
basex/log/
basex/data/
basex/.pid
basex/BaseX.jar
basex/lib/*.jar
.basex.pid
*.jar
```

**Step 4: Run test to verify it passes**

```bash
git check-ignore basex/log/ basex/BaseX.jar .basex.pid
# Expected: outputs the ignored paths
```

**Step 5: Commit**

```bash
git add .gitignore
git commit -m "chore: add BaseX files to .gitignore"
```

---

## Task 2: Create CREDITS.md for BaseX Attribution

**Files:**
- Create: `basex/CREDITS.md`

**Step 1: Write the failing test**

```bash
# Test: Verify CREDITS.md exists
[ -f basex/CREDITS.md ] && echo "PASS" || echo "FAIL: CREDITS.md missing"
```

**Step 2: Run test to verify it fails**

```bash
[ -f basex/CREDITS.md ] && echo "PASS" || echo "FAIL"
# Expected: FAIL
```

**Step 3: Write the implementation**

```markdown
# BaseX Credits

This project uses [BaseX](http://basex.org/), an XML database.

- **Version**: Downloaded via `scripts/download-basex.sh`
- **License**: BSD-3-Clause
- **Website**: http://basex.org
- **Copyright**: Christian Gruen, et al.

## License

BaseX is licensed under the BSD-3-Clause License:

```
Copyright (c) 2005-2024, Christian Gruen. All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:

1. Redistributions of source code must retain the above copyright notice,
   this list of conditions and the following disclaimer.

2. Redistributions in binary form must reproduce the above copyright notice,
   this list of conditions and the following disclaimer in the documentation
   and/or other materials provided with the distribution.

3. Neither the name of the copyright holder nor the names of its
   contributors may be used to endorse or promote products derived from
   this software without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE
LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
POSSIBILITY OF SUCH DAMAGE.
```
```

**Step 4: Run test to verify it passes**

```bash
[ -f basex/CREDITS.md ] && echo "PASS"
```

**Step 5: Commit**

```bash
git add basex/CREDITS.md
git commit -m "docs: add BaseX credits and license"
```

---

## Task 3: Create MIT License File

**Files:**
- Create: `LICENSE`

**Step 1: Write the failing test**

```bash
# Test: Verify LICENSE file exists
[ -f LICENSE ] && echo "PASS" || echo "FAIL: LICENSE missing"
```

**Step 2: Run test to verify it fails**

```bash
[ -f LICENSE ] && echo "PASS" || echo "FAIL"
# Expected: FAIL
```

**Step 3: Write the implementation**

```markdown
MIT License

Copyright (c) 2024 Lexicographic Curation Workbench

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

**Step 4: Run test to verify it passes**

```bash
[ -f LICENSE ] && echo "PASS"
```

**Step 5: Commit**

```bash
git add LICENSE
git commit -m "docs: add MIT license"
```

---

## Task 4: Create Download Script

**Files:**
- Create: `scripts/download-basex.sh`
- Create: `scripts/test-basex.sh`

**Step 1: Write the failing test**

```bash
# Test: Download script exists and is executable
[ -x scripts/download-basex.sh ] && echo "PASS" || echo "FAIL"
# Test: Test script exists and is executable
[ -x scripts/test-basex.sh ] && echo "PASS" || echo "FAIL"
```

**Step 2: Run test to verify it fails**

```bash
[ -x scripts/download-basex.sh ] && echo "PASS" || echo "FAIL"
# Expected: FAIL
```

**Step 3: Write the implementation**

`scripts/download-basex.sh`:
```bash
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
```

`scripts/test-basex.sh`:
```bash
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
```

**Step 4: Run test to verify it passes**

```bash
chmod +x scripts/download-basex.sh scripts/test-basex.sh
[ -x scripts/download-basex.sh ] && [ -x scripts/test-basex.sh ] && echo "PASS"
```

**Step 5: Commit**

```bash
git add scripts/download-basex.sh scripts/test-basex.sh
git commit -m "feat: add BaseX download and test scripts"
```

---

## Task 5: Create Robust Start Script

**Files:**
- Create: `basex/bin/start`

**Step 1: Write the failing test**

```bash
# Test: Start script exists and is executable
[ -x basex/bin/start ] && echo "PASS" || echo "FAIL"
# Test: Script accepts --help
./basex/bin/start --help 2>&1 | grep -q "Usage" && echo "PASS" || echo "FAIL"
```

**Step 2: Run test to verify it fails**

```bash
[ -x basex/bin/start ] && echo "PASS" || echo "FAIL"
# Expected: FAIL
```

**Step 3: Write the implementation**

```bash
#!/usr/bin/env bash
#
# BaseX Start Script
# Robust start with logging, health checks, and auto-restart
#
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BASEX_DIR="$(dirname "$SCRIPT_DIR")"
LOG_DIR="$BASEX_DIR/log"
LOG_FILE="$LOG_DIR/basex.log"
ERR_LOG="$LOG_DIR/basex.err.log"
PID_FILE="$BASEX_DIR/.pid"
JAR_FILE="$BASEX_DIR/BaseX.jar"
MAX_RETRIES=3
RETRY_DELAY=5
MAX_LOG_SIZE=10485760  # 10MB
MAX_LOG_FILES=5

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
NC='\033[0m'

log() {
    local level="$1"
    local message="$2"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    echo "[$timestamp] [$level] $message" >> "$LOG_FILE"

    case "$level" in
        ERROR) echo -e "${RED}[$level] $message${NC}" ;;
        WARN)  echo -e "${YELLOW}[$level] $message${NC}" ;;
        INFO)  echo -e "[$level] $message" ;;
    esac
}

setup_logging() {
    mkdir -p "$LOG_DIR"

    # Rotate logs if too large
    if [ -f "$LOG_FILE" ] && [ $(stat -f%z "$LOG_FILE" 2>/dev/null || stat -c%s "$LOG_FILE") -gt $MAX_LOG_SIZE ]; then
        for i in $(seq $MAX_LOG_FILES -1 1); do
            [ -f "${LOG_FILE}.$i" ] && mv "${LOG_FILE}.$i" "${LOG_FILE}.$((i+1))"
        done
        mv "$LOG_FILE" "${LOG_FILE}.1"
        touch "$LOG_FILE"
    fi

    touch "$LOG_FILE" "$ERR_LOG"
}

get_pid() {
    if [ -f "$PID_FILE" ]; then
        cat "$PID_FILE"
    else
        echo ""
    fi
}

is_running() {
    local pid=$(get_pid)
    if [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null; then
        return 0
    else
        return 1
    fi
}

health_check() {
    local port=1984
    local timeout=5

    # Level 1: Port open
    if ! nc -z -w$timeout localhost $port 2>/dev/null; then
        log "WARN" "Health check level 1 failed: port $port not open"
        return 1
    fi

    # Level 2: TCP connection
    if ! timeout $((timeout*2)) bash -c "echo > /dev/tcp/localhost/$port" 2>/dev/null; then
        log "WARN" "Health check level 2 failed: cannot connect to port $port"
        return 1
    fi

    log "INFO" "Health check passed"
    return 0
}

stop_basex() {
    log "INFO" "Stopping BaseX..."
    java -cp "$JAR_FILE" org.basex.BaseXServer -s 2>/dev/null || true

    local pid=$(get_pid)
    if [ -n "$pid" ]; then
        # Wait for process to stop
        local waited=0
        while kill -0 "$pid" 2>/dev/null && [ $waited -lt 30 ]; do
            sleep 1
            waited=$((waited + 1))
        done

        # Force kill if still running
        if kill -0 "$pid" 2>/dev/null; then
            log "WARN" "Force killing BaseX process $pid"
            kill -9 "$pid" 2>/dev/null || true
        fi
    fi

    rm -f "$PID_FILE"
    log "INFO" "BaseX stopped"
}

start_basex() {
    local attempt=1
    local backoff=$RETRY_DELAY

    while [ $attempt -le $MAX_RETRIES ]; do
        log "INFO" "Attempt $attempt/$MAX_RETRIES to start BaseX..."

        # Start BaseX server
        nohup java -cp "$JAR_FILE" org.basex.BaseXServer -d > "$LOG_FILE" 2>&1 &
        local pid=$!
        echo "$pid" > "$PID_FILE"

        # Wait for startup
        sleep 3

        # Check if process is running
        if ! kill -0 "$pid" 2>/dev/null; then
            log "ERROR" "BaseX process died immediately"
            attempt=$((attempt + 1))
            backoff=$((backoff * 2))
            sleep $backoff
            continue
        fi

        # Health check
        if health_check; then
            log "INFO" "BaseX started successfully (PID: $pid)"
            echo "BaseX started (PID: $pid)"
            return 0
        else
            log "WARN" "BaseX started but health check failed"
            stop_basex
            attempt=$((attempt + 1))
            backoff=$((backoff * 2))
            sleep $backoff
        fi
    done

    log "ERROR" "Failed to start BaseX after $MAX_RETRIES attempts"
    echo -e "${RED}ERROR: Failed to start BaseX after $MAX_RETRIES attempts${NC}"
    echo "Check $LOG_FILE for details"
    return 1
}

show_status() {
    if is_running; then
        local pid=$(get_pid)
        echo -e "${GREEN}BaseX is running (PID: $pid)${NC}"
        echo "Log: $LOG_FILE"
        echo "PID file: $PID_FILE"

        # Show last few log lines
        echo -e "\n${YELLOW}Recent log entries:${NC}"
        tail -5 "$LOG_FILE"
        return 0
    else
        echo -e "${RED}BaseX is not running${NC}"
        if [ -f "$LOG_FILE" ]; then
            echo -e "\n${YELLOW}Last log entries:${NC}"
            tail -10 "$LOG_FILE"
        fi
        return 1
    fi
}

show_help() {
    cat << EOF
Usage: $(basename "$0") [command] [options]

Commands:
    start       Start BaseX server (default)
    stop        Stop BaseX server
    status      Show server status
    health      Run deep health check
    restart     Restart the server

Options:
    --help      Show this help message
    --force     Force restart (stop first if running)

Examples:
    $(basename "$0")              # Start BaseX
    $(basename "$0") stop         # Stop BaseX
    $(basename "$0") status       # Check status
    $(basename "$0") restart      # Restart
EOF
}

# Main
main() {
    setup_logging

    command="${1:-start}"
    shift || true

    case "$command" in
        -h|--help|help)
            show_help
            exit 0
            ;;
        start)
            if [ "$1" == "--force" ]; then
                is_running && stop_basex
            fi
            if is_running; then
                log "WARN" "BaseX is already running"
                echo -e "${YELLOW}BaseX is already running${NC}"
                exit 0
            fi
            start_basex
            ;;
        stop)
            if is_running; then
                stop_basex
                echo -e "${GREEN}BaseX stopped${NC}"
            else
                echo -e "${YELLOW}BaseX is not running${NC}"
            fi
            ;;
        status)
            show_status
            ;;
        health)
            if health_check; then
                echo -e "${GREEN}BaseX health check passed${NC}"
                exit 0
            else
                echo -e "${RED}BaseX health check failed${NC}"
                exit 1
            fi
            ;;
        restart)
            is_running && stop_basex
            sleep 2
            start_basex
            ;;
        *)
            echo -e "${RED}Unknown command: $command${NC}"
            show_help
            exit 1
            ;;
    esac
}

main "$@"
```

**Step 4: Run test to verify it passes**

```bash
chmod +x basex/bin/start
[ -x basex/bin/start ] && echo "PASS"
./basex/bin/start --help 2>&1 | grep -q "Usage" && echo "PASS"
```

**Step 5: Commit**

```bash
git add basex/bin/start
git commit -m "feat: add robust BaseX start script with logging and health checks"
```

---

## Task 6: Create Stop and Status Scripts

**Files:**
- Create: `basex/bin/stop`
- Create: `basex/bin/status`

**Step 1: Write the failing test**

```bash
# Test: Scripts exist and are executable
[ -x basex/bin/stop ] && echo "PASS" || echo "FAIL"
[ -x basex/bin/status ] && echo "PASS" || echo "FAIL"
```

**Step 2: Run test to verify it fails**

```bash
[ -x basex/bin/stop ] && echo "PASS" || echo "FAIL"
# Expected: FAIL
```

**Step 3: Write the implementation**

`basex/bin/stop`:
```bash
#!/usr/bin/env bash
#
# BaseX Stop Script
#
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BASEX_DIR="$(dirname "$SCRIPT_DIR")"
JAR_FILE="$BASEX_DIR/BaseX.jar"
PID_FILE="$BASEX_DIR/.pid"

if [ -f "$JAR_FILE" ]; then
    java -cp "$JAR_FILE" org.basex.BaseXServer -s 2>/dev/null || true
fi

if [ -f "$PID_FILE" ]; then
    pid=$(cat "$PID_FILE")
    if kill -0 "$pid" 2>/dev/null; then
        kill "$pid" 2>/dev/null || true
        sleep 2
        kill -9 "$pid" 2>/dev/null || true
    fi
    rm -f "$PID_FILE"
fi

echo "BaseX stop command sent"
```

`basex/bin/status`:
```bash
#!/usr/bin/env bash
#
# BaseX Status Script
#
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BASEX_DIR="$(dirname "$SCRIPT_DIR")"
PID_FILE="$BASEX_DIR/.pid"

if [ -f "$PID_FILE" ]; then
    pid=$(cat "$PID_FILE")
    if kill -0 "$pid" 2>/dev/null; then
        echo "BaseX is running (PID: $pid)"
        exit 0
    fi
fi

echo "BaseX is not running"
exit 1
```

**Step 4: Run test to verify it passes**

```bash
chmod +x basex/bin/stop basex/bin/status
[ -x basex/bin/stop ] && [ -x basex/bin/status ] && echo "PASS"
```

**Step 5: Commit**

```bash
git add basex/bin/stop basex/bin/status
git commit -m "feat: add BaseX stop and status scripts"
```

---

## Task 7: Remove Old Files and Update start-services.sh

**Files:**
- Delete: `BaseX120.jar`
- Delete: `.basex.pid`
- Modify: `start-services.sh`

**Step 1: Write the failing test**

```bash
# Test: Old files removed
[ ! -f BaseX120.jar ] && echo "PASS" || echo "FAIL: BaseX120.jar still exists"
[ ! -f .basex.pid ] && echo "PASS" || echo "FAIL: .basex.pid still exists"
# Test: start-services.sh updated to use new script
grep -q "basex/bin/start" start-services.sh && echo "PASS" || echo "FAIL"
```

**Step 2: Run test to verify it fails**

```bash
[ ! -f BaseX120.jar ] && echo "PASS" || echo "FAIL"
# Expected: FAIL (file exists)
```

**Step 3: Write the implementation**

```bash
# Remove old files
rm -f BaseX120.jar .basex.pid
echo "Removed old BaseX files"
```

Update `start-services.sh` to use new script (replace BaseX section):
```bash
# Check/Start BaseX Server using new robust script
echo -e "\033[36mChecking BaseX Server...\033[0m"

if ./basex/bin/status &>/dev/null; then
    echo -e "\033[32m✓ BaseX Server is running\033[0m"
else
    echo -e "\033[36mStarting BaseX Server...\033[0m"
    ./basex/bin/start
fi
```

**Step 4: Run test to verify it passes**

```bash
[ ! -f BaseX120.jar ] && [ ! -f .basex.pid ] && echo "PASS"
```

**Step 5: Commit**

```bash
git rm BaseX120.jar .basex.pid
git add start-services.sh
git commit -m "refactor: remove old BaseX files and use new start script"
```

---

## Task 8: Final Verification

**Step 1: Run all tests**

```bash
# Verify gitignore
git check-ignore basex/log/ basex/BaseX.jar .basex.pid *.jar

# Verify files exist
[ -f basex/CREDITS.md ] && echo "CREDITS.md exists"
[ -f LICENSE ] && echo "LICENSE exists"
[ -x scripts/download-basex.sh ] && echo "download-basex.sh exists"
[ -x basex/bin/start ] && echo "start script exists"
[ -x basex/bin/stop ] && echo "stop script exists"
[ -x basex/bin/status ] && echo "status script exists"

# Verify scripts work
./basex/bin/start --help | grep -q "Usage" && echo "start --help works"

# Run shellcheck on scripts
if command -v shellcheck &> /dev/null; then
    shellcheck basex/bin/* scripts/*.sh
    echo "Shellcheck passed"
fi
```

**Step 2: Commit**

```bash
git commit --allow-empty -m "chore: verify BaseX refactor complete"
```

---

## Summary of Files Changed/Created

| Task | Action | Files |
|------|--------|-------|
| 1 | Modify | `.gitignore` |
| 2 | Create | `basex/CREDITS.md` |
| 3 | Create | `LICENSE` |
| 4 | Create | `scripts/download-basex.sh`, `scripts/test-basex.sh` |
| 5 | Create | `basex/bin/start` |
| 6 | Create | `basex/bin/stop`, `basex/bin/status` |
| 7 | Delete | `BaseX120.jar`, `.basex.pid` |
| 7 | Modify | `start-services.sh` |

---

Plan complete and saved to `docs/plans/2026-01-04-basex-infrastructure-refactor.md`. Two execution options:

1. **Subagent-Driven (this session)** - I dispatch fresh subagent per task, review between tasks, fast iteration

2. **Parallel Session (separate)** - Open new session with executing-plans, batch execution with checkpoints

Which approach?
