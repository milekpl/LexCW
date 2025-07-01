#!/usr/bin/env python3
"""
Debug script to understand the namespace situation in test databases.
"""

import os
import sys
import uuid
import tempfile

# Add parent directory to Python path for imports
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from app.database.basex_connector import BaseXConnector
from app.services.dictionary_service import DictionaryService
from app.models.entry import Entry
from app.models.sense import Sense

def main():
    print("=== Debug Namespace State in Test Database ===")
    
    # Create test database like in conftest.py
    test_db_name = f"test_ns_debug_{uuid.uuid4().hex[:8]}"
    
    connector_no_db = BaseXConnector(
        host=os.getenv('BASEX_HOST', 'localhost'),
        port=int(os.getenv('BASEX_PORT', '1984')),
        username=os.getenv('BASEX_USERNAME', 'admin'),
        password=os.getenv('BASEX_PASSWORD', 'admin'),
        database=None,
    )
    
    connector = BaseXConnector(
        host=os.getenv('BASEX_HOST', 'localhost'),
        port=int(os.getenv('BASEX_PORT', '1984')),
        username=os.getenv('BASEX_USERNAME', 'admin'),
        password=os.getenv('BASEX_PASSWORD', 'admin'),
        database=test_db_name,
    )
    
    try:
        # Create database like conftest.py
        connector_no_db.connect()
        connector_no_db.create_database(test_db_name)
        connector_no_db.disconnect()
        connector.connect()
        
        # Add initial LIFT content like conftest.py
        sample_lift = '''<?xml version="1.0" encoding="UTF-8"?>
<lift version="0.13" xmlns="http://fieldworks.sil.org/schemas/lift/0.13">
    <entry id="test_entry_1">
        <lexical-unit>
            <form lang="en"><text>test</text></form>
        </lexical-unit>
        <sense id="test_sense_1">
            <definition>
                <form lang="en"><text>A test entry</text></form>
            </definition>
            <gloss lang="en"><text>test</text></gloss>
        </sense>
    </entry>
</lift>'''
        
        connector.execute_update(f"db:add('{test_db_name}', '{sample_lift}', 'lift.xml')")
        print("Added initial LIFT content with namespace")
        
        # Create dictionary service
        service = DictionaryService(db_connector=connector)
        
        # Check namespace detection after initialization
        has_ns_initial = service._detect_namespace_usage()
        print(f"Namespace detected after initialization: {has_ns_initial}")
        
        # Check what exists in the database
        queries = [
            ("Namespaced lift elements", f'declare namespace lift = "http://fieldworks.sil.org/schemas/lift/0.13"; count(collection("{test_db_name}")//lift:lift)'),
            ("Non-namespaced lift elements", f'count(collection("{test_db_name}")//lift)'),
            ("Namespaced entry elements", f'declare namespace lift = "http://fieldworks.sil.org/schemas/lift/0.13"; count(collection("{test_db_name}")//lift:entry)'),
            ("Non-namespaced entry elements", f'count(collection("{test_db_name}")//entry)'),
        ]
        
        for name, query in queries:
            try:
                result = connector.execute_query(query)
                print(f"{name}: {result}")
            except Exception as e:
                print(f"{name}: Error - {e}")
        
        # Now create an entry through the service
        entry = Entry(
            id="service_entry_1",
            lexical_unit={"en": "searchable_word", "pl": "słowo_do_wyszukania"},
            senses=[
                Sense(
                    id="service_sense_1",
                    gloss="Searchable gloss",
                    definition="Searchable definition"
                )
            ]
        )
        
        print(f"\nCreating entry through service: {entry.id}")
        service.create_entry(entry)
        print("Entry created successfully")
        
        # Check namespace detection after creating entry
        service._has_namespace = None  # Reset cache
        has_ns_after = service._detect_namespace_usage()
        print(f"Namespace detected after creating entry: {has_ns_after}")
        
        # Check what exists in the database now
        for name, query in queries:
            try:
                result = connector.execute_query(query)
                print(f"{name}: {result}")
            except Exception as e:
                print(f"{name}: Error - {e}")
        
        # Test search functionality
        print(f"\nTesting search for 'searchable':")
        entries, total = service.search_entries("searchable")
        print(f"Search returned {len(entries)} entries, total: {total}")
        
        for entry_result in entries:
            print(f"  - {entry_result.id}: {entry_result.lexical_unit}")
        
        # Test search for 'test' (from initial data)
        print(f"\nTesting search for 'test':")
        entries, total = service.search_entries("test")
        print(f"Search returned {len(entries)} entries, total: {total}")
        
        for entry_result in entries:
            print(f"  - {entry_result.id}: {entry_result.lexical_unit}")
            
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # Cleanup
        try:
            if connector._session:
                connector.drop_database(test_db_name)
                print(f"Dropped test database: {test_db_name}")
                connector.disconnect()
        except Exception as e:
            print(f"Cleanup error: {e}")

if __name__ == "__main__":
    main()
