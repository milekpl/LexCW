#!/usr/bin/env python3
"""
Debug script to check ranges in BaseX database.
"""

import os
import sys
import tempfile
import uuid

# Add parent directory to Python path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.database.basex_connector import BaseXConnector


def debug_basex_ranges():
    """Debug ranges in test database."""
    # Create test database
    test_db_name = f"debug_{uuid.uuid4().hex[:8]}"
    
    connector = BaseXConnector(
        host=os.getenv('BASEX_HOST', 'localhost'),
        port=int(os.getenv('BASEX_PORT', '1984')),
        username=os.getenv('BASEX_USERNAME', 'admin'),
        password=os.getenv('BASEX_PASSWORD', 'admin'),
        database=None,
    )
    
    try:
        connector.connect()
        connector.create_database(test_db_name)
        
        # Add sample ranges.xml
        sample_ranges = '''<?xml version="1.0" encoding="UTF-8"?>
<lift-ranges>
    <range id="grammatical-info">
        <range-element id="noun" label="Noun">
            <description>This is a noun.</description>
        </range-element>
        <range-element id="verb" label="Verb">
            <description>This is a verb.</description>
        </range-element>
    </range>
</lift-ranges>'''
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.xml', delete=False, encoding='utf-8') as f:
            f.write(sample_ranges)
            ranges_file = f.name
            
        # Add ranges.xml using ADD command  
        print(f"Adding ranges file: {ranges_file}")
        connector.execute_command(f"ADD {ranges_file}")
        print("Added ranges.xml using ADD command")
        
        # Now let's check what's in the database
        connector.database = test_db_name
        connector.disconnect()
        connector.connect()
        
        print(f"\n=== DATABASE: {test_db_name} ===")
        
        # Check what documents exist
        try:
            docs = connector.execute_query("for $doc in collection() return db:path($doc)")
            print(f"Documents in database:\n{docs}")
        except Exception as e:
            print(f"Error listing documents: {e}")
            
        # Try different queries for ranges
        queries = [
            "collection()//lift-ranges",
            "doc('ranges.xml')",
            f"doc('{test_db_name}/ranges.xml')",
            "collection()//range",
            "//*[local-name()='lift-ranges']",
            "/*",
        ]
        
        for query in queries:
            try:
                result = connector.execute_query(query)
                print(f"\nQuery: {query}")
                print(f"Result: {result[:200]}..." if len(result) > 200 else f"Result: {result}")
            except Exception as e:
                print(f"Query: {query} - Error: {e}")
                
        # Clean up temp file
        os.unlink(ranges_file)
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        try:
            if hasattr(connector, '_session') and connector._session:
                connector.drop_database(test_db_name)
                print(f"\nDropped database: {test_db_name}")
                connector.disconnect()
        except Exception as e:
            print(f"Cleanup error: {e}")


if __name__ == "__main__":
    debug_basex_ranges()
