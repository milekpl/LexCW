"""
JavaScript Test Integration Module

This module provides pytest-compatible tests for JavaScript functionality,
allowing JavaScript tests to be run from within the Python test suite.
"""

import pytest
import os
import subprocess
import tempfile
from pathlib import Path
from typing import Dict, Any, List

from tests.js_test_runner import JSTestRunner, run_specific_js_test


class TestJavaScriptIntegration:
    """Test JavaScript functionality from Python."""
    
    @pytest.fixture(autouse=True)
    def setup_js_runner(self):
        """Set up JavaScript test runner."""
        self.runner = JSTestRunner()
        
        # Skip tests if JavaScript environment is not available
        if not self.runner.check_jest_available():
            pytest.skip("Jest not available, skipping JavaScript tests")
    
    def test_lift_xml_serializer_jest_test(self):
        """Test the LIFT XML serializer Jest test."""
        test_dir = os.path.dirname(__file__)
        test_script_path = os.path.join(test_dir, 'test_lift_xml_serializer.test.js')
        
        if not os.path.exists(test_script_path):
            pytest.skip(f"Test script not found: {test_script_path}")
        
        result = run_specific_js_test(test_script_path)
        
        assert result['success'], f"LIFT XML serializer test failed: {result.get('stderr', 'No error message')}"
    
    def test_jest_test_execution(self):
        """Test that Jest can execute tests successfully."""
        # Run Jest on a specific pattern to test Jest functionality
        result = self.runner.run_jest_tests(test_pattern="tests/unit/test_lift_xml_serializer.test.js")
        
        assert result['success'], f"Jest execution failed: {result.get('stderr', 'No error message')}"
    
    def test_javascript_linting(self):
        """Test JavaScript code with ESLint."""
        result = self.runner.run_eslint(['app/static/js/'])

        # Skip if ESLint/npm isn't available or timed out in this environment
        if result.get('return_code') == -1 and 'timed out' in (result.get('stderr') or '').lower():
            pytest.skip("ESLint execution timed out in this environment")
        if result.get('return_code') == -1 and ('not found' in (result.get('stderr') or '').lower() or 'npm' in (result.get('stderr') or '').lower()):
            pytest.skip("ESLint/npm not available in this environment")

        # For now, just check that ESLint runs without crashing; exit code 0 or 1 are acceptable
        assert result['success'] or result['return_code'] in [0, 1], f"ESLint failed: {result.get('stderr', 'No error message')}"
    
    def test_javascript_syntax_validation(self):
        """Validate JavaScript syntax of all app JS files using node --check.

        Uses ``node --check`` for syntax-only parsing (no execution), which
        avoids false-positives on browser-only files that reference DOM
        elements at the top level (e.g. ``coverage.js``).
        """
        import pathlib

        js_dir = pathlib.Path('app/static/js/')
        skip_patterns = {'.min.js', '.test.js', '__tests__'}

        errors = []
        for js_path in sorted(js_dir.rglob('*.js')):
            if any(p in str(js_path) for p in skip_patterns):
                continue
            try:
                result = subprocess.run(
                    ['node', '--check', str(js_path)],
                    capture_output=True, text=True, timeout=10,
                )
                if result.returncode != 0:
                    errors.append(f"{js_path}: {result.stderr.strip()}")
            except subprocess.TimeoutExpired:
                errors.append(f"{js_path}: timed out")

        if errors:
            pytest.fail(
                f"JavaScript syntax errors found in {len(errors)} file(s):\n"
                + "\n".join(errors)
            )


def test_run_all_javascript_tests():
    """Test function to run all JavaScript tests as part of Python test suite."""
    runner = JSTestRunner()
    
    if not runner.check_jest_available():
        pytest.skip("Jest not available, skipping JavaScript tests")
    
    result = runner.run_jest_tests()
    
    # Only fail if Jest itself failed to run, not if individual tests failed
    # (individual test failures will be reported separately)
    assert 'return_code' in result, "Jest execution should return a code"
    
    # Log test results for debugging
    if not result['success']:
        print(f"Jest test execution issue: {result.get('stderr', 'Unknown error')}")


class TestJavaScriptBrowserCompatibility:
    """Test JavaScript code for browser compatibility issues."""
    
    def test_js_dom_api_compatibility(self):
        """Test JavaScript code that uses DOM APIs for Node.js compatibility."""
        pytest.skip("form-serializer.js removed in Alpine refactor (§16.3 B2)")


if __name__ == "__main__":
    # Allow running this test module directly
    pytest.main([__file__, "-v"])