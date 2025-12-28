"""
Pytest plugin for JavaScript test integration.

This plugin allows JavaScript tests to be run as part of the Python test suite,
enabling unified test execution from VS Code.
"""

import pytest
import os
import sys
from typing import Dict, Any
from tests.js_test_runner import JSTestRunner, run_all_js_tests, run_specific_js_test


def pytest_addoption(parser):
    """Add command line options for JavaScript tests."""
    group = parser.getgroup('js-tests')
    group.addoption(
        '--js-tests',
        action='store_true',
        default=False,
        help='Also run JavaScript tests as part of the test suite'
    )
    group.addoption(
        '--js-lint',
        action='store_true',
        default=False,
        help='Run JavaScript linting as part of the test suite'
    )
    group.addoption(
        '--js-coverage',
        action='store_true',
        default=False,
        help='Generate JavaScript coverage reports'
    )


def pytest_configure(config):
    """Configure pytest for JavaScript tests."""
    config.addinivalue_line(
        "markers", "javascript: mark test as JavaScript test"
    )
    config.addinivalue_line(
        "markers", "js_lint: mark test as JavaScript linting test"
    )


@pytest.fixture(scope="session")
def js_test_runner():
    """Provide JavaScript test runner fixture."""
    return JSTestRunner()


@pytest.fixture(scope="session")
def js_test_environment():
    """Check JavaScript test environment availability."""
    runner = JSTestRunner()
    return {
        'node_available': runner.check_node_available(),
        'npm_available': runner.check_npm_available(),
        'jest_available': runner.check_jest_available(),
    }


@pytest.mark.javascript
def test_js_environment(js_test_environment):
    """Test that JavaScript testing environment is properly set up."""
    assert js_test_environment['node_available'], "Node.js is required for JavaScript tests"
    assert js_test_environment['jest_available'], "Jest is required for JavaScript tests"


@pytest.mark.javascript
def test_run_all_js_tests(js_test_runner):
    """Run all JavaScript tests as part of the Python test suite."""
    if not js_test_runner.check_jest_available():
        pytest.skip("Jest not available, skipping JavaScript tests")
    
    results = run_all_js_tests()
    
    # Report test results
    if 'jest' in results['test_results']:
        jest_result = results['test_results']['jest']
        if not jest_result['success']:
            pytest.fail(f"JavaScript tests failed: {jest_result.get('stderr', 'Unknown error')}")
    
    # Report linting results
    if 'eslint' in results['lint_results']:
        lint_result = results['lint_results']['eslint']
        if not lint_result['success']:
            pytest.fail(f"JavaScript linting failed: {lint_result.get('stderr', 'Unknown error')}")


def pytest_runtest_setup(item):
    """Skip JavaScript tests if environment is not available."""
    if 'javascript' in item.keywords or 'js_lint' in item.keywords:
        # Check if we have the js_test_environment fixture
        if 'js_test_environment' in item.fixturenames:
            # This will be handled by the fixture
            pass
        else:
            # Check environment directly
            runner = JSTestRunner()
            if not runner.check_jest_available():
                pytest.skip("Jest not available, skipping JavaScript test")


def pytest_configure_node(node):
    """Configure pytest node for JavaScript tests."""
    pass


def pytest_collection_modifyitems(config, items):
    """Modify test collection based on command line options."""
    run_js_tests = config.getoption("--js-tests")
    run_js_lint = config.getoption("--js-lint")
    
    if not run_js_tests and not run_js_lint:
        # Skip all JavaScript-related tests if not requested
        skip_js = pytest.mark.skip(reason="JavaScript tests not requested, use --js-tests or --js-lint to run them")
        for item in items:
            if 'javascript' in item.keywords or 'js_lint' in item.keywords:
                item.add_marker(skip_js)


# Add a hook to run JavaScript tests at the start of the test session
@pytest.hookimpl(tryfirst=True)
def pytest_sessionstart(session):
    """Run JavaScript tests if requested."""
    if session.config.option.js_tests or session.config.option.js_lint:
        print("Running JavaScript tests...")
        results = run_all_js_tests()
        
        if not results['overall_success']:
            # Store results in session for later use
            session.js_test_results = results
            if session.config.option.js_tests and not results['environment_check']['jest_available']:
                print("WARNING: Jest not available, JavaScript tests will be skipped")
            if session.config.option.js_lint and not results['environment_check']['npm_available']:
                print("WARNING: npm not available, JavaScript linting will be skipped")


def pytest_sessionfinish(session, exitstatus):
    """Report JavaScript test results at the end of the session."""
    if hasattr(session, 'js_test_results'):
        results = session.js_test_results
        print("\nJavaScript Test Results Summary:")
        print(f"  Environment - Node: {results['environment_check']['node_available']}, "
              f"Jest: {results['environment_check']['jest_available']}")
        
        if 'jest' in results['test_results']:
            jest_result = results['test_results']['jest']
            print(f"  Jest Tests - Success: {jest_result['success']}")
        
        if 'eslint' in results['lint_results']:
            lint_result = results['lint_results']['eslint']
            print(f"  ESLint - Success: {lint_result['success']}")
        
        print(f"  Overall JavaScript Success: {results['overall_success']}")