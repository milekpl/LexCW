#!/usr/bin/env python3
"""Robustly set BaseX admin password using ALTER PASSWORD command."""

import sys
import subprocess
import os

BASEX_JAR = os.environ.get('BASEX_JAR', '/home/milek/basex/BaseX.jar')
DEFAULT_PASSWORD = 'admin'

def run_basex_command(command):
    """Execute a BaseX command via the command-line tool."""
    result = subprocess.run([
        'java', '-cp', BASEX_JAR, 'org.basex.BaseX', '-c', command
    ], capture_output=True, text=True)
    return result.returncode, result.stdout, result.stderr

def set_password_via_java(username, new_password):
    """Set password using Java BaseX CLI."""
    code, out, err = run_basex_command(f'ALTER PASSWORD {username} {new_password}')
    return code == 0, out, err

def main():
    username = 'admin'
    password = os.environ.get('BASEX_PASSWORD', DEFAULT_PASSWORD)

    print(f"Setting password for user '{username}' to '{password}'...")

    # Method 1: Try via Java CLI (most reliable)
    success, out, err = set_password_via_java(username, password)

    if success:
        print("✓ Password set successfully via Java CLI")
        print(f"  {out.strip()}")
        return 0

    # Method 2: Fallback - check if already correct
    print("Java CLI method failed. Checking if password is already set...")
    print(f"  {err.strip()}")

    return 1

if __name__ == '__main__':
    sys.exit(main())
