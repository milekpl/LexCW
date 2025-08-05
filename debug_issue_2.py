#!/usr/bin/env python3

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.services.validation_engine import ValidationEngine

def debug_issue_2():
    """Debug the third test case for issue #2."""
    validation_engine = ValidationEngine('validation_rules.json')
    
    # Test case with all empty definitions - should fail
    entry_data_all_empty = {
        "id": "test_entry_all_empty",
        "lexical-unit": {"lang": "en"},  # Fixed: using correct structure
        "senses": [
            {
                "id": "sense1",
                "definition": {
                    "en": "",  # Source language - allowed to be empty
                    "pl": ""   # Target language - should NOT be empty
                }
            }
        ]
    }
    
    result = validation_engine.validate_json(entry_data_all_empty)
    print(f"All empty definitions - Valid: {result.is_valid}")
    if not result.is_valid:
        for error in result.errors:
            print(f"  Error: {error.message} at {error.path}")
    else:
        print("  No errors found")

if __name__ == '__main__':
    debug_issue_2()
