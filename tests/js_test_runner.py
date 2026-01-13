"""
JavaScript Test Runner for Python Integration

This module provides functionality to run JavaScript tests from within Python,
allowing for unified test execution across both Python and JavaScript codebases.
"""

import subprocess
import sys
import os
from typing import List, Dict, Any, Optional
import json
import tempfile
import logging

logger = logging.getLogger(__name__)


class JSTestRunner:
    """Run JavaScript tests from Python."""
    
    def __init__(self, project_root: str = None):
        """
        Initialize the JavaScript test runner.
        
        Args:
            project_root: Path to the project root directory. If None, uses current directory.
        """
        self.project_root = project_root or os.getcwd()
        self.package_json_path = os.path.join(self.project_root, 'package.json')
        self.jest_config_path = os.path.join(self.project_root, 'jest.config.js')
        
    def check_node_available(self) -> bool:
        """Check if Node.js is available in the system."""
        try:
            result = subprocess.run(['node', '--version'], 
                                  capture_output=True, 
                                  text=True, 
                                  timeout=10)
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False
    
    def check_npm_available(self) -> bool:
        """Check if npm is available in the system."""
        try:
            result = subprocess.run(['npm', '--version'], 
                                  capture_output=True, 
                                  text=True, 
                                  timeout=10)
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False
    
    def check_jest_available(self) -> bool:
        """Check if Jest is available (either globally or locally)."""
        try:
            # First try local Jest
            result = subprocess.run(['npx', 'jest', '--version'], 
                                  capture_output=True, 
                                  text=True, 
                                  timeout=10,
                                  cwd=self.project_root)
            if result.returncode == 0:
                return True
            
            # Then try global Jest
            result = subprocess.run(['jest', '--version'], 
                                  capture_output=True, 
                                  text=True, 
                                  timeout=10,
                                  cwd=self.project_root)
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False
    
    def run_jest_tests(self, 
                      test_pattern: str = None, 
                      coverage: bool = False, 
                      verbose: bool = False) -> Dict[str, Any]:
        """
        Run Jest tests and return results.
        
        Args:
            test_pattern: Pattern to match specific test files (e.g., '*serializer*')
            coverage: Whether to generate coverage report
            verbose: Whether to run in verbose mode
            
        Returns:
            Dictionary containing test results
        """
        if not self.check_jest_available():
            raise RuntimeError("Jest is not available. Please install Jest or run 'npm install'")
        
        cmd = ['npx', 'jest']
        
        if test_pattern:
            cmd.append(test_pattern)
        
        # Add JSON output for parsing results
        cmd.extend(['--json'])
        
        if coverage:
            cmd.append('--coverage')
        
        if verbose:
            cmd.append('--verbose')
        
        try:
            result = subprocess.run(cmd, 
                                  capture_output=True, 
                                  text=True, 
                                  timeout=180,  # Increased timeout for larger test suites
                                  cwd=self.project_root)
            
            if result.returncode == 0:
                # Parse Jest JSON output
                try:
                    output = json.loads(result.stdout)
                    return {
                        'success': True,
                        'test_results': output,
                        'stdout': result.stdout,
                        'stderr': result.stderr,
                        'return_code': result.returncode
                    }
                except json.JSONDecodeError:
                    # If JSON parsing fails, return basic success
                    return {
                        'success': True,
                        'test_results': None,
                        'stdout': result.stdout,
                        'stderr': result.stderr,
                        'return_code': result.returncode
                    }
            else:
                # Parse Jest JSON output even for failures
                try:
                    output = json.loads(result.stdout)
                    return {
                        'success': False,
                        'test_results': output,
                        'stdout': result.stdout,
                        'stderr': result.stderr,
                        'return_code': result.returncode
                    }
                except json.JSONDecodeError:
                    return {
                        'success': False,
                        'test_results': None,
                        'stdout': result.stdout,
                        'stderr': result.stderr,
                        'return_code': result.returncode
                    }
                    
        except subprocess.TimeoutExpired:
            return {
                'success': False,
                'test_results': None,
                'stdout': '',
                'stderr': 'Test execution timed out',
                'return_code': -1
            }
        except Exception as e:
            return {
                'success': False,
                'test_results': None,
                'stdout': '',
                'stderr': str(e),
                'return_code': -1
            }
    
    def run_node_script(self, script_path: str) -> Dict[str, Any]:
        """
        Run a specific Node.js script (like the existing test_form_serializer.js).
        
        Args:
            script_path: Path to the Node.js script to run
            
        Returns:
            Dictionary containing execution results
        """
        if not self.check_node_available():
            raise RuntimeError("Node.js is not available")
        
        if not os.path.exists(script_path):
            raise FileNotFoundError(f"Script not found: {script_path}")
        
        try:
            result = subprocess.run(['node', script_path], 
                                  capture_output=True, 
                                  text=True, 
                                  timeout=30,
                                  cwd=self.project_root)
            
            return {
                'success': result.returncode == 0,
                'stdout': result.stdout,
                'stderr': result.stderr,
                'return_code': result.returncode
            }
        except subprocess.TimeoutExpired:
            return {
                'success': False,
                'stdout': '',
                'stderr': 'Script execution timed out',
                'return_code': -1
            }
        except Exception as e:
            return {
                'success': False,
                'stdout': '',
                'stderr': str(e),
                'return_code': -1
            }
    
    def run_eslint(self, paths: List[str] = None) -> Dict[str, Any]:
        """
        Run ESLint for JavaScript linting.
        
        Args:
            paths: List of paths to lint. If None, lints default JS paths
            
        Returns:
            Dictionary containing linting results
        """
        if not self.check_npm_available():
            raise RuntimeError("npm is not available")
        
        cmd = ['npx', 'eslint']
        
        if paths:
            cmd.extend(paths)
        else:
            # Default to linting the JS files in the app directory
            cmd.extend(['app/static/js/', 'tests/unit/', 'tests/integration/'])
        
        cmd.extend(['--ext', '.js', '--format', 'json'])
        
        try:
            result = subprocess.run(cmd, 
                                  capture_output=True, 
                                  text=True, 
                                  timeout=30,
                                  cwd=self.project_root)
            
            try:
                lint_results = json.loads(result.stdout) if result.stdout.strip() else []
                return {
                    'success': result.returncode == 0,
                    'lint_results': lint_results,
                    'stdout': result.stdout,
                    'stderr': result.stderr,
                    'return_code': result.returncode
                }
            except json.JSONDecodeError:
                return {
                    'success': result.returncode == 0,
                    'lint_results': [],
                    'stdout': result.stdout,
                    'stderr': result.stderr,
                    'return_code': result.returncode
                }
                
        except subprocess.TimeoutExpired:
            return {
                'success': False,
                'lint_results': [],
                'stdout': '',
                'stderr': 'ESLint execution timed out',
                'return_code': -1
            }
        except Exception as e:
            return {
                'success': False,
                'lint_results': [],
                'stdout': '',
                'stderr': str(e),
                'return_code': -1
            }


def run_all_js_tests(project_root: str = None) -> Dict[str, Any]:
    """
    Run all JavaScript tests in the project.
    
    Args:
        project_root: Path to project root. If None, uses current directory.
        
    Returns:
        Dictionary with comprehensive test results
    """
    runner = JSTestRunner(project_root)
    
    results = {
        'environment_check': {
            'node_available': runner.check_node_available(),
            'npm_available': runner.check_npm_available(),
            'jest_available': runner.check_jest_available(),
        },
        'test_results': {},
        'lint_results': {},
        'overall_success': True
    }
    
    # Check if environment is ready
    if not results['environment_check']['node_available']:
        results['overall_success'] = False
        logger.error("Node.js is not available")
    
    if not results['environment_check']['jest_available']:
        results['overall_success'] = False
        logger.error("Jest is not available")
    
    if results['overall_success']:
        # Run Jest tests
        try:
            jest_results = runner.run_jest_tests()
            results['test_results']['jest'] = jest_results
            results['overall_success'] = results['overall_success'] and jest_results['success']
        except Exception as e:
            logger.error(f"Error running Jest tests: {e}")
            results['overall_success'] = False
        
        # Run ESLint
        try:
            lint_results = runner.run_eslint()
            results['lint_results']['eslint'] = lint_results
            results['overall_success'] = results['overall_success'] and lint_results['success']
        except Exception as e:
            logger.error(f"Error running ESLint: {e}")
            results['overall_success'] = False
    
    return results


def run_specific_js_test(test_file_path: str) -> Dict[str, Any]:
    """
    Run a specific JavaScript test file.
    
    Args:
        test_file_path: Path to the JavaScript test file to run
        
    Returns:
        Dictionary with test results
    """
    runner = JSTestRunner()
    
    # If it's a Jest test file (ends with .test.js or .spec.js), use Jest
    if test_file_path.endswith(('.test.js', '.spec.js')):
        # Extract the pattern from the path
        relative_path = os.path.relpath(test_file_path, os.getcwd())
        return runner.run_jest_tests(test_pattern=relative_path)
    else:
        # For other JS files, run with Node directly
        return runner.run_node_script(test_file_path)


if __name__ == "__main__":
    # Run all JavaScript tests when executed directly
    print("Running all JavaScript tests...")
    results = run_all_js_tests()
    
    print(f"Environment check - Node: {results['environment_check']['node_available']}, "
          f"Jest: {results['environment_check']['jest_available']}")
    
    if 'jest' in results['test_results']:
        jest_result = results['test_results']['jest']
        print(f"Jest tests - Success: {jest_result['success']}, Return code: {jest_result['return_code']}")
        if jest_result['stderr']:
            print(f"Jest stderr: {jest_result['stderr']}")
    
    if 'eslint' in results['lint_results']:
        lint_result = results['lint_results']['eslint']
        print(f"ESLint - Success: {lint_result['success']}, Return code: {lint_result['return_code']}")
        if lint_result['stderr']:
            print(f"ESLint stderr: {lint_result['stderr']}")
    
    print(f"Overall success: {results['overall_success']}")
    sys.exit(0 if results['overall_success'] else 1)