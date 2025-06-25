"""
Simple test script to verify BaseX functionality.
"""

import os
import sys
import logging
from dotenv import load_dotenv

# Add the parent directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.database.basex_connector import BaseXConnector

def main():
    """Main entry point for the test script."""
    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    logger = logging.getLogger(__name__)
    
    # Load environment variables
    load_dotenv()
    
    # Get configuration from environment variables
    host = os.getenv('BASEX_HOST', 'localhost')
    port = int(os.getenv('BASEX_PORT', '1984'))
    username = os.getenv('BASEX_USERNAME', 'admin')
    password = os.getenv('BASEX_PASSWORD', 'admin')
    database = os.getenv('BASEX_DATABASE', 'dictionary')
    
    print(f"Connecting to BaseX at {host}:{port} with user {username}")
    
    # Create a BaseX connector
    connector = BaseXConnector(
        host=host,
        port=port,
        username=username,
        password=password,
        database=database
    )
    
    try:
        # Connect to the database
        if not connector.connect():
            print("Failed to connect to the database.")
            sys.exit(1)
            
        print("Successfully connected to BaseX server")
        
        # Test 1: Check if database exists
        result = connector.execute_query("LIST")
        print(f"Available databases: {result}")
        
        # Test 2: Create test database and check if it works
        test_db_name = "test_import_db"
        try:
            # Drop if exists
            if test_db_name in (connector.execute_query("LIST") or ""):
                print(f"Dropping existing test database: {test_db_name}")
                connector.execute_update(f"DROP DB {test_db_name}")
            
            # Create a new test database with a simple document
            print(f"Creating test database: {test_db_name}")
            connector.execute_update(f'CREATE DB {test_db_name} "<root><test>This is a test</test></root>"')
            
            # Test the collection() function
            collection_query = f"xquery collection('{test_db_name}')/root/test/text()"
            result = connector.execute_query(collection_query)
            print(f"Collection query result: {result}")
            
            # Try the db:open() function to see if it's available
            try:
                db_open_query = f"xquery db:open('{test_db_name}')/root/test/text()"
                result = connector.execute_query(db_open_query)
                print(f"db:open query result: {result}")
                print("db:open function is available")
            except Exception as e:
                print(f"db:open function is NOT available: {e}")
                
            # Drop the test database
            print(f"Dropping test database: {test_db_name}")
            connector.execute_update(f"DROP DB {test_db_name}")
            
        except Exception as e:
            print(f"Error during database test: {e}")
            raise
            
        # Test 3: Try to create a database from a LIFT file
        lift_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), 
                                "sample-lift-file", "sample-lift-file.lift")
        lift_file = lift_file.replace('\\', '/')
        test_lift_db = "test_lift_db"
        
        try:
            # Drop if exists
            if test_lift_db in (connector.execute_query("LIST") or ""):
                print(f"Dropping existing test LIFT database: {test_lift_db}")
                connector.execute_update(f"DROP DB {test_lift_db}")
            
            # Create from LIFT file
            print(f"Creating test LIFT database from {lift_file}")
            connector.execute_update(f'CREATE DB {test_lift_db} "{lift_file}"')
            
            # Test counting entries
            count_query = f"xquery count(collection('{test_lift_db}')//*:entry)"
            count = connector.execute_query(count_query)
            print(f"Found {count} entries in the LIFT file")
            
            # Drop the test database
            print(f"Dropping test LIFT database: {test_lift_db}")
            connector.execute_update(f"DROP DB {test_lift_db}")
            
        except Exception as e:
            print(f"Error during LIFT database test: {e}")
            raise
        
        print("All tests completed successfully")
        
    except Exception as e:
        print(f"CRITICAL ERROR: {e}")
        logger.error('Error: %s', e, exc_info=True)
        sys.exit(1)
    finally:
        if connector:
            connector.disconnect()
            print("Disconnected from BaseX server")


if __name__ == '__main__':
    main()
