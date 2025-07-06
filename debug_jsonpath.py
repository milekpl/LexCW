#!/usr/bin/env python3
"""
Debug JSONPath behavior for sense validation.
"""

import sys
import os
sys.path.insert(0, os.path.abspath('.'))

import jsonpath_ng

def debug_jsonpath():
    """Debug what JSONPath is finding in the data."""
    
    # Test data with no senses
    data_no_senses = {
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
    
    # Test data with empty senses array
    data_empty_senses = {
        "id": "test_variant_entry",
        "lexical_unit": {"pl": "testando"},
        "relations": [
            {
                "type": "_component-lexeme",
                "ref": "base_entry_id",
                "traits": {"variant-type": "Unspecified Variant"}
            }
        ],
        "senses": []
    }
    
    # Test data with empty sense object
    data_empty_sense_object = {
        "id": "test_variant_entry",
        "lexical_unit": {"pl": "testando"},
        "relations": [
            {
                "type": "_component-lexeme",
                "ref": "base_entry_id",
                "traits": {"variant-type": "Unspecified Variant"}
            }
        ],
        "senses": [{}]
    }
    
    # JSONPath for sense IDs
    jsonpath_expr = jsonpath_ng.parse("$.senses[*].id")
    
    print("Test 1: No senses field")
    matches1 = jsonpath_expr.find(data_no_senses)
    print(f"Matches: {len(matches1)}")
    for match in matches1:
        print(f"  Match: {match.value} at {match.full_path}")
    
    print("\nTest 2: Empty senses array")
    matches2 = jsonpath_expr.find(data_empty_senses)
    print(f"Matches: {len(matches2)}")
    for match in matches2:
        print(f"  Match: {match.value} at {match.full_path}")
    
    print("\nTest 3: Empty sense object")
    matches3 = jsonpath_expr.find(data_empty_sense_object)
    print(f"Matches: {len(matches3)}")
    for match in matches3:
        print(f"  Match: {match.value} at {match.full_path}")

if __name__ == "__main__":
    debug_jsonpath()
