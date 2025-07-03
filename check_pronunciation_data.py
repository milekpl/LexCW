#!/usr/bin/env python3
"""
Check if pronunciation data exists in entries and debug the template rendering.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from app.services.dictionary_service import DictionaryService
from flask import current_app
import json

def main():
    print("Testing pronunciation data in entries...")
    
    # Initialize Flask app
    app = create_app()
    
    with app.app_context():
        # Initialize service
        service = current_app.injector.get(DictionaryService)
    
    # Test with Protestantism
    print("\n1. Checking Protestantism entry:")
    try:
        protestantism = service.get_entry("Protestantism")
        if protestantism:
            print(f"  Entry found: {protestantism.lexical_unit}")
            print(f"  Pronunciations type: {type(protestantism.pronunciations)}")
            print(f"  Pronunciations value: {protestantism.pronunciations}")
            if protestantism.pronunciations:
                print(f"  Pronunciations JSON: {json.dumps(protestantism.pronunciations, indent=2)}")
            else:
                print("  No pronunciations found")
        else:
            print("  Protestantism entry not found")
    except Exception as e:
        print(f"  Error getting Protestantism: {e}")
    
    # Test with a simple search
    print("\n2. Searching for entries with pronunciations:")
    try:
        search_result = service.search_entries("", limit=10)
        entries, total_count = search_result  # Unpack the tuple
        print(f"  Found {len(entries)} entries total (out of {total_count})")
        
        # Check first few entries to see their pronunciation data
        for i, entry in enumerate(entries[:5]):
            print(f"\n  Entry {i+1}: {entry.lexical_unit}")
            print(f"    ID: {entry.id}")
            print(f"    Has pronunciations attr: {hasattr(entry, 'pronunciations')}")
            if hasattr(entry, 'pronunciations'):
                print(f"    Pronunciations type: {type(entry.pronunciations)}")
                print(f"    Pronunciations value: {entry.pronunciations}")
                print(f"    Pronunciations bool: {bool(entry.pronunciations)}")
        
        entries_with_pronunciations = []
        
        for entry in entries:
            if hasattr(entry, 'pronunciations') and entry.pronunciations:
                entries_with_pronunciations.append(entry)
                if len(entries_with_pronunciations) <= 3:  # Show details for first 3
                    print(f"  Found: {entry.lexical_unit}")
                    print(f"    ID: {entry.id}")
                    print(f"    Pronunciations: {entry.pronunciations}")
        
        print(f"\n  Total entries with pronunciations: {len(entries_with_pronunciations)}")
        
        if entries_with_pronunciations:
            print(f"\n3. Testing template data conversion for first entry:")
            test_entry = entries_with_pronunciations[0]
            print(f"  Entry: {test_entry.lexical_unit}")
            print(f"  Raw pronunciations: {test_entry.pronunciations}")
            
            # Simulate the template logic
            pronunciations = test_entry.pronunciations or {}
            print(f"  After default({{}}): {pronunciations}")
            
            pronunciation_array = []
            if pronunciations and isinstance(pronunciations, dict):
                for writing_system, value in pronunciations.items():
                    pronunciation_array.append({
                        'type': writing_system,
                        'value': value,
                        'audio_file': "",
                        'is_default': True
                    })
            
            print(f"  Converted to array: {json.dumps(pronunciation_array, indent=2)}")
        
    except Exception as e:
        print(f"  Error searching entries: {e}")

if __name__ == "__main__":
    main()
