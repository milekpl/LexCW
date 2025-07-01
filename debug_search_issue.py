#!/usr/bin/env python3
"""
Debug script to investigate why search is returning empty results.
"""

import logging
import sys
import os

# Add the current directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app, injector
from app.services.dictionary_service import DictionaryService
from app.models.entry import Entry
from app.models.sense import Sense

# Configure logging to see what's happening
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

def main():
    """Main function to debug search issue."""
    print("=== DEBUG SEARCH ISSUE ===")
    
    # Create app and get service
    app = create_app("testing")
    
    with app.app_context():
        dict_service = injector.get(DictionaryService)
        
        # Create a test entry
        test_entry = Entry(
            id="debug_search_test",
            lexical_unit={"en": "searchable_test_word", "pl": "słowo_testowe"},
            senses=[
                Sense(
                    id="debug_sense_1",
                    gloss="Test gloss for searching",
                    definition="Test definition for searching"
                )
            ]
        )
        
        try:
            # Create the entry
            print("Creating test entry...")
            result = dict_service.create_entry(test_entry)
            print(f"Entry created: {result}")
            
            # Try to retrieve the entry to confirm it exists
            print("\nRetrieving entry to confirm it exists...")
            retrieved = dict_service.get_entry("debug_search_test")
            print(f"Retrieved entry: {retrieved.id if retrieved else 'None'}")
            
            # Now try to search for it
            print("\nSearching for 'searchable'...")
            entries, total = dict_service.search_entries("searchable")
            print(f"Search returned {total} total results, {len(entries)} entries")
            for entry in entries:
                print(f"  - {entry.id}: {entry.lexical_unit}")
            
            print("\nSearching for 'test'...")
            entries, total = dict_service.search_entries("test")
            print(f"Search returned {total} total results, {len(entries)} entries")
            for entry in entries:
                print(f"  - {entry.id}: {entry.lexical_unit}")
            
            print("\nSearching for 'word'...")
            entries, total = dict_service.search_entries("word")
            print(f"Search returned {total} total results, {len(entries)} entries")
            for entry in entries:
                print(f"  - {entry.id}: {entry.lexical_unit}")
            
            print("\nSearching for exact lexical unit 'searchable_test_word'...")
            entries, total = dict_service.search_entries("searchable_test_word")
            print(f"Search returned {total} total results, {len(entries)} entries")
            for entry in entries:
                print(f"  - {entry.id}: {entry.lexical_unit}")
            
            # Let's also check what raw entries are in the database
            print("\nGetting all entries...")
            all_entries, all_total = dict_service.search_entries("", limit=100)
            print(f"Total entries in database: {all_total}")
            for entry in all_entries:
                print(f"  - {entry.id}: {entry.lexical_unit}")
                
        except Exception as e:
            print(f"Error during testing: {e}")
            import traceback
            traceback.print_exc()
        
        finally:
            # Clean up
            try:
                dict_service.delete_entry("debug_search_test")
                print("\nTest entry cleaned up")
            except:
                pass

if __name__ == "__main__":
    main()
