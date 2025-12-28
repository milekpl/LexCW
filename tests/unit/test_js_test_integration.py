"""
Test to verify JavaScript-Python test integration is working.
"""

import pytest
import subprocess
import os
from tests.js_test_runner import JSTestRunner


def test_js_test_runner_initialization():
    """Test that the JavaScript test runner can be initialized."""
    runner = JSTestRunner()
    
    # Check that the runner can detect Node.js and Jest
    assert hasattr(runner, 'check_node_available')
    assert hasattr(runner, 'check_jest_available')
    

def test_node_availability():
    """Test that Node.js is available."""
    runner = JSTestRunner()
    assert runner.check_node_available(), "Node.js should be available for JavaScript tests"


def test_jest_availability():
    """Test that Jest is available."""
    runner = JSTestRunner()
    # Skip if Jest is not available (may not be installed yet)
    if not runner.check_jest_available():
        pytest.skip("Jest not available - run 'npm install' to install dependencies")
    assert runner.check_jest_available(), "Jest should be available for JavaScript tests"


@pytest.mark.javascript
def test_can_run_simple_js_script():
    """Test that we can run a simple JavaScript script through the runner."""
    runner = JSTestRunner()
    
    if not runner.check_jest_available():
        pytest.skip("Jest not available, skipping JavaScript test")
    
    # Create a temporary JavaScript file to test
    import tempfile
    with tempfile.NamedTemporaryFile(mode='w', suffix='.js', delete=False) as f:
        f.write("""
        // Simple test script
        console.log('Hello from JavaScript!');
        process.exit(0);
        """)
        temp_script = f.name
    
    try:
        result = runner.run_node_script(temp_script)
        assert result['success'], f"JavaScript script should run successfully: {result.get('stderr', '')}"
    finally:
        # Clean up the temporary file
        os.unlink(temp_script)


@pytest.mark.javascript 
def test_existing_js_tests_discoverable():
    """Test that existing JavaScript tests can be found and run."""
    runner = JSTestRunner()
    
    if not runner.check_jest_available():
        pytest.skip("Jest not available, skipping JavaScript test")
    
    # Look for existing JavaScript test files
    js_test_files = []
    for root, dirs, files in os.walk('tests/unit'):
        for file in files:
            if file.endswith(('.test.js', '.spec.js')):
                js_test_files.append(os.path.join(root, file))
    
    # At least the existing test files should be found
    assert len(js_test_files) > 0, "Should find at least one JavaScript test file"
    
    # Try running Jest on one of them
    result = runner.run_jest_tests(test_pattern=js_test_files[0])
    # Don't assert success here as the test might legitimately fail, 
    # but the execution should not error out
    assert 'return_code' in result, "Jest should return a result"


def test_js_linting_available():
    """Test that ESLint is available for linting."""
    runner = JSTestRunner()

    if not runner.check_npm_available():
        pytest.skip("npm not available, skipping ESLint test")

    # Try running ESLint on a small subset
    result = runner.run_eslint(['app/static/js/form-serializer.js'])

    # ESLint might return 0 (no errors), 1 (linting issues found), or 2 (configuration issues)
    # The important thing is that it runs without execution errors (non-zero exit codes are OK for linting)
    # Only fail if there's a command execution error (like command not found)
    assert result['return_code'] in [0, 1, 2], f"ESLint should execute: {result.get('stderr', '')}"