#!/usr/bin/env python3
"""
Debug Entry model instantiation to see what happens with senses.
"""

import sys
import os
sys.path.insert(0, os.path.abspath('.'))

from app.models.entry import Entry
import json

def debug_entry_instantiation():
    """Debug Entry model creation and to_dict conversion."""
    
    # Test without senses field
    variant_entry_data = {
        "id": "test_variant_entry",
        "lexical_unit": {"pl": "testando"},
        "relations": [
            {
                "type": "_component-lexeme",
                "ref": "base_entry_id",
                "traits": {"variant-type": "Unspecified Variant"}
            }
        ]
    }
    
    print("Original data:")
    print(json.dumps(variant_entry_data, indent=2))
    
    entry = Entry(**variant_entry_data)
    
    print("\nEntry.senses attribute:")
    print(f"Type: {type(entry.senses)}")
    print(f"Value: {entry.senses}")
    print(f"Length: {len(entry.senses) if entry.senses else 'None'}")
    
    entry_dict = entry.to_dict()
    print("\nEntry.to_dict() result:")
    print(json.dumps(entry_dict, indent=2, default=str))
    
    if 'senses' in entry_dict:
        print(f"\nSenses in dict: {entry_dict['senses']}")
        print(f"Senses type: {type(entry_dict['senses'])}")
        print(f"Senses length: {len(entry_dict['senses'])}")

if __name__ == "__main__":
    debug_entry_instantiation()
