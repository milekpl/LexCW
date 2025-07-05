#!/usr/bin/env python3
"""
Form Serializer Test Runner

Simple script to run all form serializer tests with proper output formatting.
This can be used for manual testing, CI/CD, or development validation.

Usage:
    python run_form_serializer_tests.py
    python run_form_serializer_tests.py --js-only
    python run_form_serializer_tests.py --py-only
"""

import subprocess
import sys
import argparse
from pathlib import Path


def run_javascript_tests():
    """Run the JavaScript/Node.js tests."""
    print("=" * 60)
    print("🔧 Running JavaScript Form Serializer Tests")
    print("=" * 60)
    
    script_dir = Path(__file__).parent
    js_test_file = script_dir / "tests" / "test_form_serializer.js"
    
    if not js_test_file.exists():
        print("❌ JavaScript test file not found:", js_test_file)
        return False
    
    try:
        result = subprocess.run(
            ["node", str(js_test_file)],
            cwd=script_dir,
            capture_output=True,
            text=True,
            timeout=30
        )
        
        print(result.stdout)
        if result.stderr:
            print("STDERR:", result.stderr)
        
        success = result.returncode == 0
        if success:
            print("✅ JavaScript tests completed successfully!")
        else:
            print("❌ JavaScript tests failed!")
        
        return success
        
    except subprocess.TimeoutExpired:
        print("❌ JavaScript tests timed out after 30 seconds")
        return False
    except FileNotFoundError:
        print("❌ Node.js not found. Please install Node.js to run JavaScript tests.")
        return False
    except Exception as e:
        print(f"❌ Error running JavaScript tests: {e}")
        return False


def run_python_tests():
    """Run the Python/Selenium tests."""
    print("=" * 60)
    print("🐍 Running Python Form Serializer Tests")
    print("=" * 60)
    
    script_dir = Path(__file__).parent
    py_test_file = script_dir / "tests" / "test_form_serializer_unit.py"
    
    if not py_test_file.exists():
        print("❌ Python test file not found:", py_test_file)
        return False
    
    try:
        # Check if pytest is available
        subprocess.run(["pytest", "--version"], capture_output=True, check=True)
        
        result = subprocess.run(
            [
                "pytest", 
                str(py_test_file), 
                "-v",
                "--tb=short",
                "-x"  # Stop on first failure
            ],
            cwd=script_dir,
            timeout=120  # 2 minutes timeout
        )
        
        success = result.returncode == 0
        if success:
            print("✅ Python tests completed successfully!")
        else:
            print("❌ Python tests failed!")
        
        return success
        
    except subprocess.CalledProcessError:
        print("❌ pytest not found. Please install pytest to run Python tests:")
        print("   pip install pytest selenium")
        return False
    except subprocess.TimeoutExpired:
        print("❌ Python tests timed out after 2 minutes")
        return False
    except Exception as e:
        print(f"❌ Error running Python tests: {e}")
        return False


def check_prerequisites():
    """Check if required tools are available."""
    print("🔍 Checking prerequisites...")
    
    issues = []
    
    # Check Node.js
    try:
        result = subprocess.run(["node", "--version"], capture_output=True, text=True)
        if result.returncode == 0:
            print(f"✅ Node.js: {result.stdout.strip()}")
        else:
            issues.append("Node.js not working properly")
    except FileNotFoundError:
        issues.append("Node.js not found")
    
    # Check Python
    try:
        print(f"✅ Python: {sys.version.split()[0]}")
    except Exception:
        issues.append("Python not working properly")
    
    # Check pytest
    try:
        result = subprocess.run(["pytest", "--version"], capture_output=True, text=True)
        if result.returncode == 0:
            print(f"✅ pytest: {result.stdout.strip().split()[0]}")
        else:
            issues.append("pytest not working properly")
    except FileNotFoundError:
        issues.append("pytest not found (run: pip install pytest selenium)")
    
    if issues:
        print("\n⚠️  Issues found:")
        for issue in issues:
            print(f"   - {issue}")
        print("\nSome tests may not run. See README for installation instructions.")
    
    return len(issues) == 0


def main():
    """Main test runner function."""
    parser = argparse.ArgumentParser(description="Run form serializer tests")
    parser.add_argument("--js-only", action="store_true", help="Run only JavaScript tests")
    parser.add_argument("--py-only", action="store_true", help="Run only Python tests")
    parser.add_argument("--no-prereq-check", action="store_true", help="Skip prerequisite check")
    
    args = parser.parse_args()
    
    print("🧪 Form Serializer Test Suite")
    print("=" * 60)
    
    if not args.no_prereq_check:
        check_prerequisites()
        print()
    
    results = []
    
    # Run JavaScript tests
    if not args.py_only:
        js_success = run_javascript_tests()
        results.append(("JavaScript", js_success))
        print()
    
    # Run Python tests
    if not args.js_only:
        py_success = run_python_tests()
        results.append(("Python", py_success))
        print()
    
    # Summary
    print("=" * 60)
    print("📊 Test Summary")
    print("=" * 60)
    
    all_passed = True
    for test_type, success in results:
        status = "✅ PASSED" if success else "❌ FAILED"
        print(f"{test_type} tests: {status}")
        if not success:
            all_passed = False
    
    if all_passed and results:
        print("\n🎉 All tests passed! Form serializer is working correctly.")
        return 0
    elif results:
        print("\n💥 Some tests failed. Check output above for details.")
        return 1
    else:
        print("\n⚠️  No tests were run.")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
