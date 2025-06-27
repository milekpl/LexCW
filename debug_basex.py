#!/usr/bin/env python3
"""
Debug script to test BaseX integration and API setup
"""
import sys
import os
sys.path.insert(0, os.path.abspath('.'))

from app import create_app
from app.database.basex_connector import BaseXConnector
from app.services.dictionary_service import DictionaryService
import tempfile
import uuid

def test_basex_setup():
    """Test BaseX database setup"""
    print("Testing BaseX setup...")
    
    test_db_name = f"test_{uuid.uuid4().hex[:8]}"
    
    connector = BaseXConnector(
        host='localhost',
        port=1984,
        username='admin',
        password='admin',
        database=test_db_name
    )
    
    try:
        # Connect and create test database
        print(f"Connecting to BaseX...")
        connector.connect()
        print("Connected successfully")
        
        # Create empty test database
        print(f"Creating database: {test_db_name}")
        connector.create_database(test_db_name)
        print("Database created")
        
        # Create sample data
        sample_lift = '''<?xml version="1.0" encoding="UTF-8"?>
<lift version="0.13" xmlns="http://code.google.com/p/lift-standard">
    <entry id="test_entry_1">
        <lexical-unit>
            <form lang="en"><text>test</text></form>
        </lexical-unit>
        <sense id="test_sense_1">
            <definition>
                <form lang="en"><text>A test entry</text></form>
            </definition>
            <gloss lang="pl"><text>test</text></gloss>
        </sense>
    </entry>
</lift>'''
        
        # Add sample data to database
        print("Adding sample data...")
        with tempfile.NamedTemporaryFile(mode='w', suffix='.xml', delete=False, encoding='utf-8') as f:
            f.write(sample_lift)
            temp_file = f.name
        
        try:
            # Try different approaches to add data
            connector.execute_query(f"db:add('{test_db_name}', doc('{temp_file}'))")
            print("Sample data added successfully")
        except Exception as e:
            print(f"Failed to add sample data: {e}")
            # Try alternative approach
            try:
                connector.execute_query(f"db:replace('{test_db_name}', 'test.xml', doc('{temp_file}'))")
                print("Sample data added via replace")
            except Exception as e2:
                print(f"Also failed with replace: {e2}")
        
        # Clean up temp file
        try:
            os.unlink(temp_file)
        except OSError:
            pass
            
        # Test query
        print("Testing database query...")
        result = connector.execute_query("count(//entry)")
        print(f"Number of entries: {result}")
        
        # Test service
        print("Testing dictionary service...")
        dict_service = DictionaryService(db_connector=connector)
        entries, total = dict_service.list_entries()
        print(f"Service found {total} entries")
        
        # Test Flask app
        print("Testing Flask app...")
        app = create_app('testing')
        app.dict_service = dict_service
        
        with app.test_client() as client:
            response = client.get('/api/entries/')
            print(f"API response status: {response.status_code}")
            if response.status_code == 200:
                data = response.get_json()
                print(f"API returned {len(data.get('entries', []))} entries")
            else:
                print(f"API error: {response.data}")
                
        return True
        
    except Exception as e:
        print(f"Error in BaseX setup: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        # Cleanup
        try:
            if connector.session:
                connector.drop_database(test_db_name)
                print(f"Dropped test database: {test_db_name}")
                connector.disconnect()
        except Exception as e:
            print(f"Error during cleanup: {e}")

if __name__ == "__main__":
    success = test_basex_setup()
    print(f"Test {'PASSED' if success else 'FAILED'}")
