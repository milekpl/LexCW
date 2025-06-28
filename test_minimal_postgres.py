#!/usr/bin/env python3
"""
Minimal PostgreSQL connection test to isolate encoding issues.
"""
import os
import sys
import psycopg2
import psycopg2.extras


def test_basic_connection():
    """Test basic PostgreSQL connection with minimal configuration."""
    print("Testing minimal PostgreSQL connection...")
    print(f"Python version: {sys.version}")
    print(f"Default encoding: {sys.getdefaultencoding()}")
    print(f"File system encoding: {sys.getfilesystemencoding()}")
    
    # Print current environment
    print("\nRelevant environment variables:")
    for var in ['LC_ALL', 'LC_CTYPE', 'LANG', 'PYTHONIOENCODING']:
        value = os.environ.get(var, 'Not set')
        print(f"  {var}: {value}")
    
    # Test connection parameters
    params = {
        'host': 'localhost',
        'port': 5432,
        'dbname': 'dictionary_analytics', 
        'user': 'dict_user',
        'password': 'dict_pass'
    }
    
    print(f"\nAttempting connection with params:")
    for key, value in params.items():
        if key == 'password':
            print(f"  {key}: {'*' * len(value)}")
        else:
            print(f"  {key}: {value}")
    
    try:
        # Method 1: Direct connection string
        print("\n--- Method 1: Direct connection string ---")
        conn_str = f"host={params['host']} port={params['port']} dbname={params['dbname']} user={params['user']} password={params['password']}"
        conn = psycopg2.connect(conn_str)
        print("✓ Direct connection string: SUCCESS")
        conn.close()
        
    except Exception as e:
        print(f"✗ Direct connection string: FAILED - {e}")
        print(f"Error type: {type(e).__name__}")
        
    try:
        # Method 2: Keyword arguments
        print("\n--- Method 2: Keyword arguments ---")
        conn = psycopg2.connect(**params)
        print("✓ Keyword arguments: SUCCESS")
        conn.close()
        
    except Exception as e:
        print(f"✗ Keyword arguments: FAILED - {e}")
        print(f"Error type: {type(e).__name__}")
        
    try:
        # Method 3: With cursor factory
        print("\n--- Method 3: With RealDictCursor ---")
        conn = psycopg2.connect(**params, cursor_factory=psycopg2.extras.RealDictCursor)
        print("✓ RealDictCursor: SUCCESS")
        conn.close()
        
    except Exception as e:
        print(f"✗ RealDictCursor: FAILED - {e}")
        print(f"Error type: {type(e).__name__}")
    
    # Test simple query if any connection succeeded
    try:
        print("\n--- Testing simple query ---")
        conn = psycopg2.connect(**params)
        with conn.cursor() as cursor:
            cursor.execute("SELECT version()")
            result = cursor.fetchone()
            print(f"✓ PostgreSQL version: {result[0]}")
        conn.close()
        
    except Exception as e:
        print(f"✗ Query test: FAILED - {e}")


if __name__ == "__main__":
    test_basic_connection()
