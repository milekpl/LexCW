#!/bin/bash
# Bash script to clean up all __pycache__ directories in the project
# Usage: Run this script from the project root

set -e

echo "Searching for __pycache__ directories..."

# Find and count __pycache__ directories
pycache_count=$(find . -type d -name '__pycache__' 2>/dev/null | wc -l)

if [ "$pycache_count" -eq 0 ]; then
    echo "No __pycache__ directories found."
    exit 0
fi

# Remove all __pycache__ directories
find . -type d -name '__pycache__' -exec rm -rf {} + 2>/dev/null || true

echo "Cleanup complete. Removed $pycache_count __pycache__ directories."
