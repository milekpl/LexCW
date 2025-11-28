#!/usr/bin/env bash
# Quick script to summarize integration test results

cd "$(dirname "$0")"

echo "Running integration tests (this may take a few minutes)..."
echo ""

source .venv/bin/activate 2>/dev/null || true

python -m pytest tests/integration/ -m integration --tb=no -q 2>&1 | tail -5
