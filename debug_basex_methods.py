#!/usr/bin/env python3
"""
Debug script to check BaseX session methods
"""
import sys
import os
sys.path.insert(0, os.path.abspath('.'))

from app.database.basex_connector import BaseXConnector

def test_basex_methods():
    """Test BaseX session methods"""
    print("Testing BaseX session methods...")
    
    connector = BaseXConnector(
        host='localhost',
        port=1984,
        username='admin',
        password='admin',
        database='dictionary'
    )
    
    try:
        connector.connect()
        print("Connected successfully")
        
        # Check available methods
        print("Available methods on BaseX session:")
        session = connector.session
        for method in dir(session):
            if not method.startswith('_'):
                print(f"  - {method}")
        
        # Test command execution
        print("\nTesting command execution...")
        
        # Test LIST command
        try:
            result = session.execute("LIST")
            print(f"LIST command result: {result}")
        except Exception as e:
            print(f"LIST command failed: {e}")
        
        # Test XQUERY command
        try:
            result = session.execute("XQUERY count(//entry)")
            print(f"XQUERY command result: {result}")
        except Exception as e:
            print(f"XQUERY command failed: {e}")
        
        # Test INFO command
        try:
            result = session.execute("INFO")
            print(f"INFO command result: {result}")
        except Exception as e:
            print(f"INFO command failed: {e}")
        
        connector.disconnect()
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_basex_methods()
