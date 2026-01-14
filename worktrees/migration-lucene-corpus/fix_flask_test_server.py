#!/usr/bin/env python3
"""Fix the flask_test_server fixture to return base_url instead of tuple."""

import sys

# Read the file
with open('tests/e2e/conftest.py', 'r') as f:
    lines = f.readlines()

# Find and fix the flask_test_server fixture
for i in range(len(lines)):
    if 'def flask_test_server(configured_flask_app):' in lines[i]:
        # Check if this is the function-scoped fixture
        if i > 0 and '@pytest.fixture(scope="function")' in lines[i-1]:
            print(f"Found function-scoped flask_test_server at line {i+1}")
            # Update the function signature
            lines[i] = 'def flask_test_server(configured_flask_app) -> str:\n'
            # Update the docstring
            if '"""Backward compatible fixture name."""' in lines[i+1]:
                lines[i+1] = '    """Backward compatible fixture name - returns base URL string."""\n'
            # Replace the return statement
            if 'return configured_flask_app' in lines[i+2]:
                lines[i+2] = '    app, base_url = configured_flask_app\n'
                lines.insert(i+3, '    return base_url\n')
            print("Fixed flask_test_server fixture")
            break

# Write the file back
with open('tests/e2e/conftest.py', 'w') as f:
    f.writelines(lines)

print("File updated successfully")
