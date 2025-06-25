#!/usr/bin/env python3
"""
BaseX Connection Test Script

This script tests if you can connect to BaseX server.
Run this before starting the Flask app to verify your BaseX setup.
"""

import sys
import os

# Add the app directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from BaseXClient import Session as BaseXSession
    print("✓ BaseXClient library is installed")
except ImportError:
    print("✗ BaseXClient library not found")
    print("  Install with: pip install BaseXClient")
    sys.exit(1)

# Configuration
BASEX_HOST = "localhost"
BASEX_PORT = 1984
BASEX_USERNAME = "admin"
BASEX_PASSWORD = "admin"
BASEX_DATABASE = "dictionary"

def test_basex_connection():
    """Test BaseX server connection."""
    print(f"\nTesting BaseX connection to {BASEX_HOST}:{BASEX_PORT}")
    print(f"Username: {BASEX_USERNAME}")
    print(f"Database: {BASEX_DATABASE}")
    print("-" * 50)
    
    try:
        # Try to connect
        print("1. Connecting to BaseX server...")
        session = BaseXSession(BASEX_HOST, BASEX_PORT, BASEX_USERNAME, BASEX_PASSWORD)
        print("✓ Connected successfully")
        
        # List databases
        print("2. Listing databases...")
        result = session.execute("LIST")
        print(f"✓ Available databases:\n{result}")
        
        # Try to open/create the dictionary database
        print(f"3. Opening/creating database '{BASEX_DATABASE}'...")
        try:
            session.execute(f"OPEN {BASEX_DATABASE}")
            print(f"✓ Database '{BASEX_DATABASE}' opened")
        except:
            print(f"  Database '{BASEX_DATABASE}' doesn't exist, creating it...")
            session.execute(f"CREATE DATABASE {BASEX_DATABASE}")
            print(f"✓ Database '{BASEX_DATABASE}' created")
        
        # Test a simple query
        print("4. Testing XQuery...")
        result = session.execute("xquery <test>Hello BaseX!</test>")
        print(f"✓ XQuery test result: {result}")
        
        # Close connection
        session.close()
        print("\n🎉 BaseX connection test PASSED!")
        print("You can now run the Flask app with BaseX integration.")
        return True
        
    except Exception as e:
        print(f"\n❌ BaseX connection test FAILED!")
        print(f"Error: {e}")
        print("\nTroubleshooting:")
        print("1. Make sure BaseX server is running:")
        print("   - Download BaseX from https://basex.org/download/")
        print("   - Extract and run: ./bin/basexserver (Linux/Mac) or bin\\basexserver.bat (Windows)")
        print(f"2. Check if server is listening on {BASEX_HOST}:{BASEX_PORT}")
        print(f"3. Verify username/password: {BASEX_USERNAME}/{BASEX_PASSWORD}")
        print("4. Check firewall settings")
        return False

if __name__ == "__main__":
    success = test_basex_connection()
    sys.exit(0 if success else 1)
