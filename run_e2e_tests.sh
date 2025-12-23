#!/bin/bash

# Run E2E tests one by one with timeout
LOG_DIR="e2e_test_logs"
mkdir -p "$LOG_DIR"

TESTS=(
    "test_debug_page.py"
    "test_language_selector.py"
    "test_pos_ui.py"
    "test_ranges_ui_playwright.py"
    "test_all_ranges_dropdowns_playwright.py"
    "test_settings_page_playwright.py"
    "test_annotations_playwright.py"
    "test_custom_fields_playwright.py"
    "test_delete_entry.py"
    "test_settings_page_functionality.py"
    "test_sense_deletion.py"
    "test_sorting_and_editing.py"
    "test_validation_playwright.py"
    "test_relations_variants_ui_playwright.py"
)

echo "Starting E2E test run at $(date)"
echo "========================================"

PASSED=0
FAILED=0
TIMEOUT=0

for test in "${TESTS[@]}"; do
    echo ""
    echo "Running: $test"
    echo "----------------------------------------"
    
    LOG_FILE="$LOG_DIR/${test%.py}.log"
    
    # Run with 3 minute timeout
    timeout 180 .venv/bin/python -m pytest "tests/e2e/$test" -v --tb=short > "$LOG_FILE" 2>&1
    EXIT_CODE=$?
    
    if [ $EXIT_CODE -eq 0 ]; then
        echo "✓ PASSED: $test"
        PASSED=$((PASSED + 1))
    elif [ $EXIT_CODE -eq 124 ]; then
        echo "⏱ TIMEOUT: $test (exceeded 3 minutes)"
        TIMEOUT=$((TIMEOUT + 1))
        echo "TIMEOUT: exceeded 3 minutes" >> "$LOG_FILE"
    else
        echo "✗ FAILED: $test (exit code: $EXIT_CODE)"
        FAILED=$((FAILED + 1))
        # Show last 20 lines of failure
        echo "Last 20 lines:"
        tail -20 "$LOG_FILE"
    fi
done

echo ""
echo "========================================"
echo "Test Summary:"
echo "  Passed:  $PASSED"
echo "  Failed:  $FAILED"
echo "  Timeout: $TIMEOUT"
echo "  Total:   ${#TESTS[@]}"
echo "========================================"
echo "Logs saved to: $LOG_DIR/"
echo "Completed at $(date)"
