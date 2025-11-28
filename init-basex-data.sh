#!/usr/bin/env bash
# Initialize BaseX database with sample LIFT data

set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

echo "Initializing BaseX database with sample LIFT data..."

# Make sure BaseX is running
if ! nc -z localhost 1984 2>/dev/null && ! timeout 2 bash -c "</dev/tcp/localhost/1984" 2>/dev/null; then
    echo "Error: BaseX is not running. Please run ./start-services.sh first."
    exit 1
fi

# Check if database already has data
echo "Checking if database already has data..."
ENTRY_COUNT=$(python3 -c "
import sys
sys.path.insert(0, '$SCRIPT_DIR')
from app.database.basex_connector import BaseXConnector
from app.services.dictionary_service import DictionaryService

connector = BaseXConnector('localhost', 1984, 'admin', 'admin', 'dictionary')
try:
    connector.connect()
    dict_service = DictionaryService(connector)
    _, count = dict_service.list_entries(limit=1)
    print(count)
finally:
    connector.disconnect()
" 2>/dev/null || echo "0")

if [ "$ENTRY_COUNT" -gt "0" ]; then
    echo "Database already contains $ENTRY_COUNT entries."
    read -p "Do you want to reinitialize and replace all data? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Skipping initialization."
        exit 0
    fi
fi

# Import the sample LIFT file
echo "Importing sample LIFT data..."
cd "$SCRIPT_DIR"

# Use virtual environment Python if available
if [ -f ".venv/bin/python" ]; then
    PYTHON=".venv/bin/python"
else
    PYTHON="python3"
fi

$PYTHON -m scripts.import_lift --init \
    sample-lift-file/sample-lift-file.lift \
    sample-lift-file/sample-lift-file.lift-ranges

echo ""
echo "✓ BaseX database initialized successfully!"
echo ""
echo "You can now run integration tests or start the application."
