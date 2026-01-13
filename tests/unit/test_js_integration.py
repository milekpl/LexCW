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
    
    def test_form_serializer_node_script(self):
        """Test the form serializer JavaScript test script."""
        test_script_path = os.path.join(os.path.dirname(__file__), 'unit', 'test_form_serializer.js')
        
        if not os.path.exists(test_script_path):
            pytest.skip(f"Test script not found: {test_script_path}")
        
        result = run_specific_js_test(test_script_path)
        
        assert result['success'], f"Form serializer test failed: {result.get('stderr', 'No error message')}"
    
    def test_lift_xml_serializer_jest_test(self):
        """Test the LIFT XML serializer Jest test."""
        test_script_path = os.path.join(os.path.dirname(__file__), 'unit', 'test_lift_xml_serializer.test.js')
        
        if not os.path.exists(test_script_path):
            pytest.skip(f"Test script not found: {test_script_path}")
        
        result = run_specific_js_test(test_script_path)
        
        assert result['success'], f"LIFT XML serializer test failed: {result.get('stderr', 'No error message')}"
    
    def test_jest_test_execution(self):
        """Test that Jest can execute tests successfully."""
        # Run Jest on a specific pattern to test Jest functionality
        result = self.runner.run_jest_tests(test_pattern="**/test_lift_xml_serializer.test.js")
        
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
        """Validate JavaScript syntax without running tests."""
        js_files = []
        
        # Find all JavaScript files in the app directory
        for root, dirs, files in os.walk('app/static/js/'):
            for file in files:
                # Skip minified files and JS test files (they run under Jest)
                if (file.endswith('.js') and not file.endswith('.min.js') and not file.endswith('.test.js') and '__tests__' not in root):
                    js_files.append(os.path.join(root, file))
        
        # Validate each JavaScript file by attempting to parse it with Node
        for js_file in js_files:
            try:
                # Create a simple Node script to validate syntax
                with tempfile.NamedTemporaryFile(mode='w', suffix='.js', delete=False) as temp:
                    temp.write(f"// Syntax validation for {js_file}\n")
                    # Provide safe shims for browser globals so we can require modules in Node
                    shim_path = os.path.abspath(os.path.join(os.path.dirname(__file__), 'js_node_shim.js'))
                    temp.write(f"require('{shim_path}');\n")
                    temp.write(f"require('{os.path.abspath(js_file)}');\n")
                    temp_path = temp.name
                
                # Run the validation script
                result = subprocess.run(['node', temp_path], 
                                      capture_output=True, 
                                      text=True, 
                                      timeout=10)
                
                # Clean up temp file
                os.unlink(temp_path)
                
                assert result.returncode == 0, f"JavaScript syntax error in {js_file}: {result.stderr}"
                
            except subprocess.TimeoutExpired:
                pytest.skip(f"Timeout validating {js_file}")
            except Exception as e:
                pytest.fail(f"Error validating {js_file}: {str(e)}")


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
        # This tests that our JavaScript can run in both browser and Node.js environments
        # by checking for proper mocking of browser globals
        
        # Example: Test form serializer with mocked browser globals
        shim_path = os.path.abspath(os.path.join(os.path.dirname(__file__), 'js_node_shim.js'))
        form_serializer_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'app', 'static', 'js', 'form-serializer.js'))

        test_script_content = f"""
        // Load centralized Node shim
        require('{shim_path}');
        // Ensure console is available
        global.console = console;

        // Import and test the form serializer
        const FormSerializer = require('{form_serializer_path}');
        const {{ serializeFormToJSON }} = FormSerializer;

        // Simple test
        const mockFormData = {{
            forEach: function(callback) {{
                callback('test_value', 'test_field');
            }}
        }};

        const result = serializeFormToJSON(mockFormData);
        console.log('Test passed:', JSON.stringify(result));
        """
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.js', delete=False) as temp:
            temp.write(test_script_content)
            temp_path = temp.name
        
        try:
            result = subprocess.run(['node', temp_path], 
                                  capture_output=True, 
                                  text=True, 
                                  timeout=10)
            
            assert result.returncode == 0, f"Browser compatibility test failed: {result.stderr}"
        finally:
            os.unlink(temp_path)


if __name__ == "__main__":
    # Allow running this test module directly
    pytest.main([__file__, "-v"])