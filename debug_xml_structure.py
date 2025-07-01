#!/usr/bin/env python3
"""
Debug script to examine the actual XML structure of created entries.
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
    print("=== Debug Entry XML Structure ===")
    
    # Create test database
    test_db_name = f"test_xml_debug_{uuid.uuid4().hex[:8]}"
    
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
        # Create database
        connector_no_db.connect()
        connector_no_db.create_database(test_db_name)
        connector_no_db.disconnect()
        
        # Connect to the database
        connector.connect()
        
        # Create dictionary service
        service = DictionaryService(db_connector=connector)
        
        # Create an entry using the service
        entry = Entry(
            id="xml_debug_entry",
            lexical_unit={"en": "searchable_word", "pl": "słowo_do_wyszukania"},
            senses=[
                Sense(
                    id="xml_debug_sense",
                    gloss="Searchable gloss",
                    definition="Searchable definition"
                )
            ]
        )
        
        print(f"Creating entry: {entry.id}")
        service.create_entry(entry)
        print("Entry created successfully")
        
        # Now query the database to see the actual XML structure
        has_ns = service._detect_namespace_usage()
        print(f"Namespace detected: {has_ns}")
        
        # Get the entire entry XML
        if has_ns:
            prologue = "declare namespace lift = \"http://fieldworks.sil.org/schemas/lift/0.13\";"
            entry_query = f"{prologue} collection('{test_db_name}')//lift:entry[@id='xml_debug_entry']"
        else:
            entry_query = f"collection('{test_db_name}')//entry[@id='xml_debug_entry']"
            
        print(f"Entry query: {entry_query}")
        
        result = connector.execute_query(entry_query)
        print(f"Raw XML result:")
        print(result)
        
        # Test specific searches that should match the entry
        test_queries = [
            ("lexical_unit search", f"{prologue if has_ns else ''} collection('{test_db_name}')//lift:entry[contains(lower-case(lexical-unit/form/text), 'searchable')]" if has_ns else f"collection('{test_db_name}')//entry[contains(lower-case(lexical-unit/form/text), 'searchable')]"),
            ("gloss search", f"{prologue if has_ns else ''} collection('{test_db_name}')//lift:entry[contains(lower-case(sense/gloss), 'searchable')]" if has_ns else f"collection('{test_db_name}')//entry[contains(lower-case(sense/gloss), 'searchable')]"),
        ]
        
        for name, query in test_queries:
            print(f"\n{name} query: {query}")
            try:
                result = connector.execute_query(query)
                print(f"Result: {result[:200] if result else 'No result'}")
            except Exception as e:
                print(f"Error: {e}")
        
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
