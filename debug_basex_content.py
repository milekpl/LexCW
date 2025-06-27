#!/usr/bin/env python3
"""
Debug script to test BaseX database content
"""
import sys
import os
sys.path.insert(0, os.path.abspath('.'))

from app.database.basex_connector import BaseXConnector
import tempfile
import uuid

def test_basex_content():
    """Test BaseX database content"""
    print("Testing BaseX database content...")
    
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
        connector.connect()
        
        # Create empty test database
        connector.create_database(test_db_name)
        print(f"Created database: {test_db_name}")
        
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
        with tempfile.NamedTemporaryFile(mode='w', suffix='.xml', delete=False, encoding='utf-8') as f:
            f.write(sample_lift)
            temp_file = f.name
        
        # Use BaseX ADD command
        result = connector.execute_command(f"ADD {temp_file}")
        print(f"ADD command result: {result}")
        
        # Clean up temp file
        os.unlink(temp_file)
        
        # Test different queries
        print("Testing queries...")
        
        # Open the database first
        connector.execute_command(f"OPEN {test_db_name}")
        print(f"Opened database: {test_db_name}")
        
        # List database info
        result = connector.execute_command("INFO")
        print(f"Database info: {result[:200]}...")  # Truncate output
        
        # Test XQuery count
        result = connector.execute_query("count(.//entry)")
        print(f"Entry count: {result}")
        
        # Test XQuery list entries
        result = connector.execute_query(".//entry")
        print(f"Entries: {result}")
        
        # Test root elements
        result = connector.execute_query("/*")
        print(f"Root elements: {result}")
        
        # Test if anything is in the database
        result = connector.execute_query("count(.)")
        print(f"Total nodes: {result}")
        
        return True
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        # Cleanup
        try:
            if connector.session:
                connector.drop_database(test_db_name)
                connector.disconnect()
        except Exception as e:
            print(f"Error during cleanup: {e}")

if __name__ == "__main__":
    success = test_basex_content()
    print(f"Test {'PASSED' if success else 'FAILED'}")
