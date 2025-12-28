#!/usr/bin/env python3
"""
Demonstration script for the integrated JavaScript and Python testing system.

This script shows how JavaScript tests can be run from Python, enabling
unified test execution from VS Code.
"""

import sys
import os
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from tests.js_test_runner import JSTestRunner, run_all_js_tests


def main():
    print("🔍 Integrated JavaScript and Python Testing System")
    print("=" * 55)
    
    print("\n1. Checking JavaScript test environment...")
    runner = JSTestRunner()
    
    print(f"   ✓ Node.js available: {runner.check_node_available()}")
    print(f"   ✓ npm available: {runner.check_npm_available()}")
    print(f"   ✓ Jest available: {runner.check_jest_available()}")
    
    if not all([
        runner.check_node_available(),
        runner.check_jest_available()
    ]):
        print("\n❌ Required tools not available. Please install Node.js and run 'npm install'")
        return 1
    
    print("\n2. Running JavaScript tests via Python...")
    results = run_all_js_tests()
    
    print(f"   ✓ Jest tests executed: {results['test_results'].get('jest', {}).get('success', False)}")
    print(f"   ✓ ESLint executed: {results['lint_results'].get('eslint', {}).get('success', False) if results['lint_results'] else False}")
    
    # Show summary
    print("\n3. Test Results Summary:")
    if 'jest' in results['test_results']:
        jest_result = results['test_results']['jest']
        if jest_result.get('test_results'):
            # Jest provides detailed results in JSON format
            num_test_suites = jest_result['test_results'].get('numTotalTestSuites', 0)
            num_tests = jest_result['test_results'].get('numTotalTests', 0)
            num_passed = jest_result['test_results'].get('numPassedTests', 0)
            num_failed = jest_result['test_results'].get('numFailedTests', 0)
            
            print(f"   🧪 Test Suites: {num_test_suites} total")
            print(f"   ✅ Tests: {num_passed} passed, {num_failed} failed, {num_tests} total")
        else:
            print(f"   🧪 Jest execution: {'Success' if jest_result['success'] else 'Failed'}")
    
    if 'eslint' in results['lint_results']:
        lint_result = results['lint_results']['eslint']
        print(f"   🔍 Linting: {'Success' if lint_result['success'] else 'Issues found'}")
    
    print(f"\n4. Overall JavaScript Test Status: {'✅ PASS' if results['overall_success'] else '❌ FAIL'}")
    
    print("\n5. Available npm scripts:")
    print("   • npm test ...................... Run Jest tests")
    print("   • npm run test:js .............. Run JavaScript tests only") 
    print("   • npm run test:python .......... Run Python tests only")
    print("   • npm run test:python-with-js ... Run Python tests with JavaScript")
    print("   • npm run lint:js .............. Run ESLint")
    
    print("\n6. Available pytest options:")
    print("   • pytest --js-tests ............ Run Python + JavaScript tests")
    print("   • pytest --js-lint ............. Run Python + JavaScript linting")
    print("   • pytest --js-tests --js-lint .. Run Python + JS tests + linting")
    
    print("\n🎉 The integrated testing system is ready!")
    print("   You can now run all tests (Python + JavaScript) from VS Code.")
    
    return 0 if results['overall_success'] else 1


if __name__ == "__main__":
    sys.exit(main())