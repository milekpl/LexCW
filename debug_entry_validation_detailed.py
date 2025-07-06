#!/usr/bin/env python3
"""
Debug exactly where the validation error comes from.
"""

import sys
import os
sys.path.insert(0, os.path.abspath('.'))

from app.models.entry import Entry
from app.services.validation_engine import ValidationEngine

def debug_entry_validation_step_by_step():
    """Debug Entry model validation step by step."""
    
    # Create variant entry without senses field
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
    
    print("Step 1: Create Entry object")
    entry = Entry(**variant_entry_data)
    print(f"Entry created successfully")
    print(f"Entry.senses: {entry.senses}")
    print(f"Entry.senses type: {type(entry.senses)}")
    print(f"Entry.senses length: {len(entry.senses)}")
    
    print("\nStep 2: Convert to dict")
    entry_dict = entry.to_dict()
    print(f"Entry dict senses: {entry_dict.get('senses', 'NOT_FOUND')}")
    
    print("\nStep 3: Test validation engine directly on dict")
    engine = ValidationEngine()
    result = engine.validate_json(entry_dict)
    print(f"Dict validation result: {result.is_valid}")
    for error in result.errors:
        print(f"  Error: {error.message} (rule: {error.rule_id}, path: {error.path})")
    
    print("\nStep 4: Test Entry.validate() method")
    try:
        entry_valid = entry.validate()
        print(f"Entry validation result: {entry_valid}")
    except Exception as e:
        print(f"Entry validation failed with exception: {e}")
        
    print("\nStep 5: Test individual sense objects")
    for i, sense in enumerate(entry.senses):
        print(f"Sense {i}: {sense}")
        print(f"  ID: {getattr(sense, 'id', 'NO_ID')}")
        print(f"  Dict: {sense.to_dict() if hasattr(sense, 'to_dict') else 'NO_TO_DICT'}")

if __name__ == "__main__":
    debug_entry_validation_step_by_step()
