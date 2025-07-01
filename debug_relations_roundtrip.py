#!/usr/bin/env python3
"""
Debug script to test relations round-trip functionality.
"""

import os
import sys

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app, injector
from app.models.entry import Entry
from app.services.dictionary_service import DictionaryService

def debug_relations_roundtrip():
    """Debug relations round-trip."""
    app = create_app('testing')
    
    with app.app_context():
        dict_service = injector.get(DictionaryService)
        
        print("=== Debug Relations Round-trip ===")
        
        # Create entry
        entry = Entry(lexical_unit={"en": "test"})
        print(f"1. Created entry: {entry.id}")
        print(f"   Initial relations: {len(entry.relations)}")
        
        # Save entry
        entry_id = dict_service.create_entry(entry)
        print(f"2. Saved entry with ID: {entry_id}")
        
        # Add relations
        entry.add_relation("synonym", "change_123")
        entry.add_relation("hypernym", "action_456")
        print(f"3. Added relations, now has: {len(entry.relations)}")
        for rel in entry.relations:
            print(f"   - {rel.type}: {rel.ref}")
        
        # Convert to dict to see serialization
        entry_dict = entry.to_dict()
        print(f"4. Entry.to_dict() relations: {entry_dict.get('relations', [])}")
        
        # Update entry
        print("5. About to update entry...")
        dict_service.update_entry(entry)
        print("6. Updated entry")
        
        # Retrieve entry
        retrieved_entry = dict_service.get_entry(entry_id)
        print(f"6. Retrieved entry: {retrieved_entry.id}")
        print(f"   Retrieved relations: {len(retrieved_entry.relations)}")
        for rel in retrieved_entry.relations:
            print(f"   - {rel.type}: {rel.ref}")

if __name__ == "__main__":
    debug_relations_roundtrip()
