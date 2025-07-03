"""Debug the range mapping issue."""
from __future__ import annotations

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app

app = create_app()

with app.app_context():
    from app.services.dictionary_service import DictionaryService
    
    dict_service = app.injector.get(DictionaryService)
    ranges = dict_service.get_lift_ranges()
    
    print("Available ranges:")
    print(list(ranges.keys()))
    
    print("\nTesting mappings:")
    # Test the mappings
    type_mappings = {
        'relation-type': ['lexical-relation', 'lexical-relations', 'relation-types'],
        'etymology-types': ['etymology', 'etymologies'],
    }
    
    for requested_type, possible_keys in type_mappings.items():
        print(f"\nFor '{requested_type}', trying: {possible_keys}")
        found = False
        for alt_key in possible_keys:
            if alt_key in ranges:
                print(f"  ✓ Found '{alt_key}' in ranges")
                found = True
                break
            else:
                print(f"  ✗ '{alt_key}' not found")
        
        if not found:
            print(f"  ERROR: No mapping found for '{requested_type}'")
