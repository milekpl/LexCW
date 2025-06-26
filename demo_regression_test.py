#!/usr/bin/env python3
"""
Regression test demonstration script.

This script demonstrates how the dashboard test can catch regressions
if debug information is accidentally added back to the homepage.
"""

import tempfile
import shutil
import subprocess
import sys
from pathlib import Path


def create_broken_template():
    """Create a version of the template with debug info to demonstrate test failure."""
    template_path = Path("app/templates/index.html")
    
    # Read current template
    with open(template_path, 'r') as f:
        content = f.read()
    
    # Add debug info that should cause test to fail
    debug_line = '                    <!-- Debug info -->\n                    <li class="list-group-item small text-muted">\n                        Debug: {{ system_status | tojson }}\n                    </li>\n'
    
    # Insert debug line before closing </ul> tag
    modified_content = content.replace(
        '                </ul>',
        debug_line + '                </ul>'
    )
    
    return modified_content


def main():
    """Demonstrate the regression test."""
    template_path = Path("app/templates/index.html")
    
    # Backup original template
    with open(template_path, 'r') as f:
        original_content = f.read()
    
    print("🧪 Demonstrating regression test...")
    print("1. Running test with clean template (should PASS)...")
    
    # Run test with clean template
    result = subprocess.run([
        sys.executable, '-m', 'pytest', 
        'tests/test_dashboard.py::TestDashboard::test_homepage_does_not_contain_debug_info',
        '-v'
    ], capture_output=True, text=True)
    
    if result.returncode == 0:
        print("   ✅ Test PASSED (no debug info found)")
    else:
        print("   ❌ Test FAILED unexpectedly")
        print(result.stdout)
        print(result.stderr)
        return
    
    print("\n2. Adding debug info back to template...")
    
    # Create broken template
    broken_content = create_broken_template()
    
    # Write broken template
    with open(template_path, 'w') as f:
        f.write(broken_content)
    
    print("3. Running test with debug info added (should FAIL)...")
    
    # Run test with broken template
    result = subprocess.run([
        sys.executable, '-m', 'pytest', 
        'tests/test_dashboard.py::TestDashboard::test_homepage_does_not_contain_debug_info',
        '-v'
    ], capture_output=True, text=True)
    
    if result.returncode != 0:
        print("   ✅ Test FAILED as expected (debug info detected)")
        print("   📋 Test output shows the regression was caught:")
        # Show relevant part of the failure
        lines = result.stdout.split('\n')
        for line in lines:
            if 'FAILED' in line or 'AssertionError' in line or 'assert' in line:
                print(f"      {line}")
    else:
        print("   ❌ Test PASSED unexpectedly (regression not caught)")
        print(result.stdout)
    
    print("\n4. Restoring original template...")
    
    # Restore original template
    with open(template_path, 'w') as f:
        f.write(original_content)
    
    print("5. Running test again to confirm restoration (should PASS)...")
    
    # Final test to confirm restoration
    result = subprocess.run([
        sys.executable, '-m', 'pytest', 
        'tests/test_dashboard.py::TestDashboard::test_homepage_does_not_contain_debug_info',
        '-v'
    ], capture_output=True, text=True)
    
    if result.returncode == 0:
        print("   ✅ Test PASSED (template restored successfully)")
    else:
        print("   ❌ Test FAILED (restoration issue)")
        print(result.stdout)
        print(result.stderr)
    
    print("\n🎉 Regression test demonstration complete!")
    print("📝 The test successfully catches when debug info is accidentally added back.")


if __name__ == "__main__":
    main()
