#!/usr/bin/env python3
"""
Debug script to examine search query construction and execution.
"""

import os
import sys
import uuid

# Add parent directory to Python path for imports
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from app.database.basex_connector import BaseXConnector
from app.services.dictionary_service import DictionaryService
from app.models.entry import Entry
from app.models.sense import Sense

def main():
    print("=== Debug Search Query Construction ===")
    
    # Create test database
    test_db_name = f"test_search_debug_{uuid.uuid4().hex[:8]}"
    
    connector = BaseXConnector(
        host=os.getenv('BASEX_HOST', 'localhost'),
        port=int(os.getenv('BASEX_PORT', '1984')),
        username=os.getenv('BASEX_USERNAME', 'admin'),
        password=os.getenv('BASEX_PASSWORD', 'admin'),
        database=test_db_name,
    )
    
    try:
        # First create connector without database to create the database
        connector_no_db = BaseXConnector(
            host=os.getenv('BASEX_HOST', 'localhost'),
            port=int(os.getenv('BASEX_PORT', '1984')),
            username=os.getenv('BASEX_USERNAME', 'admin'),
            password=os.getenv('BASEX_PASSWORD', 'admin'),
            database=None,
        )
        
        # Connect and create the test database
        connector_no_db.connect()
        connector_no_db.create_database(test_db_name)
        connector_no_db.disconnect()
        
        # Now connect with the database
        connector.connect()
        
        # Initialize database with LIFT structure
        sample_lift = '''<?xml version="1.0" encoding="UTF-8"?>
<lift version="0.13" xmlns="http://fieldworks.sil.org/schemas/lift/0.13">
    <entry id="debug_entry_1">
        <lexical-unit>
            <form lang="en"><text>searchable_word</text></form>
            <form lang="pl"><text>słowo_do_wyszukania</text></form>
        </lexical-unit>
        <sense id="debug_sense_1">
            <definition>
                <form lang="en"><text>Searchable definition</text></form>
            </definition>
            <gloss lang="en"><text>Searchable gloss</text></gloss>
        </sense>
    </entry>
</lift>'''
        
        # Add the data
        connector.execute_update(f"db:add('{test_db_name}', '{sample_lift}', 'lift.xml')")
        print(f"Created test database: {test_db_name}")
        
        # Create dictionary service
        service = DictionaryService(db_connector=connector)
        
        # Debug namespace detection
        has_ns = service._detect_namespace_usage()
        print(f"Namespace detected: {has_ns}")
        
        # Debug element path construction
        entry_path = service._query_builder.get_element_path("entry", has_ns)
        print(f"Entry path: {entry_path}")
        
        # Debug raw queries
        query = "searchable"
        q_escaped = query.replace("'", "''")
        
        # Build search conditions manually to see what they look like
        conditions = []
        conditions.append(f"(some $form in $entry/lexical-unit/form/text satisfies contains(lower-case($form), '{q_escaped.lower()}'))")
        conditions.append(f"(some $gloss in $entry/sense/gloss/text satisfies contains(lower-case($gloss), '{q_escaped.lower()}'))")
        conditions.append(f"(some $def in $entry/sense/definition/form/text satisfies contains(lower-case($def), '{q_escaped.lower()}'))")
        
        search_condition = " or ".join(conditions)
        print(f"Search conditions: {search_condition}")
        
        # Build and execute count query
        count_query = f"count(for $entry in collection('{test_db_name}')//{entry_path} where {search_condition} return $entry)"
        print(f"Count query: {count_query}")
        
        try:
            count_result = connector.execute_query(count_query)
            print(f"Count result: {count_result}")
        except Exception as e:
            print(f"Count query failed: {e}")
        
        # Build and execute search query
        search_query = f"for $entry in collection('{test_db_name}')//{entry_path} where {search_condition} return $entry"
        print(f"Search query: {search_query}")
        
        try:
            search_result = connector.execute_query(search_query)
            print(f"Search result length: {len(search_result) if search_result else 0}")
            if search_result:
                print(f"Search result preview: {search_result[:200]}...")
        except Exception as e:
            print(f"Search query failed: {e}")
        
        # Test service method
        print("\n=== Testing service method ===")
        try:
            entries, total = service.search_entries("searchable")
            print(f"Service returned {len(entries)} entries, total: {total}")
            for entry in entries:
                print(f"  - {entry.id}: {entry.lexical_unit}")
        except Exception as e:
            print(f"Service search failed: {e}")
            
    except Exception as e:
        print(f"Error: {e}")
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
