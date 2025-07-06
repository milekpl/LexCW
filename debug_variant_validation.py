#!/usr/bin/env python3
"""
Debug test to understand why variant entry validation is failing.
"""

import sys
import os
sys.path.insert(0, os.path.abspath('.'))

from app.services.validation_engine import ValidationEngine

def debug_variant_entry_validation():
    """Debug what's happening with variant entry validation."""
    
    # Test with no senses field
    variant_entry_data_no_senses = {
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
    
    # Test with empty senses array
    variant_entry_data_empty_senses = {
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
    
    # Test with empty sense object
    variant_entry_data_empty_sense_object = {
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
    
    engine = ValidationEngine()
    
    print("Test 1: No senses field")
    result1 = engine.validate_json(variant_entry_data_no_senses)
    print(f"Valid: {result1.is_valid}")
    for error in result1.errors:
        print(f"  Error: {error.message} (rule: {error.rule_id})")
    
    print("\nTest 2: Empty senses array")
    result2 = engine.validate_json(variant_entry_data_empty_senses)
    print(f"Valid: {result2.is_valid}")
    for error in result2.errors:
        print(f"  Error: {error.message} (rule: {error.rule_id})")
    
    print("\nTest 3: Empty sense object")
    result3 = engine.validate_json(variant_entry_data_empty_sense_object)
    print(f"Valid: {result3.is_valid}")
    for error in result3.errors:
        print(f"  Error: {error.message} (rule: {error.rule_id})")

if __name__ == "__main__":
    debug_variant_entry_validation()
