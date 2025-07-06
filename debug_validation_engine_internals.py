#!/usr/bin/env python3
"""
Debug what happens inside the validation engine for sense validation.
"""

import sys
import os
sys.path.insert(0, os.path.abspath('.'))

from app.services.validation_engine import ValidationEngine
import jsonpath_ng

def debug_validation_engine_internals():
    """Debug what happens inside the validation engine."""
    
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
        ],
        "senses": []
    }
    
    print("Original data:")
    print(f"  senses: {variant_entry_data.get('senses', 'NOT_FOUND')}")
    
    engine = ValidationEngine()
    
    # Manually check rule R2.1.1
    rule_config = engine.rules.get('R2.1.1')
    if rule_config:
        print(f"\nRule R2.1.1: {rule_config['name']}")
        print(f"  path: {rule_config['path']}")
        print(f"  condition: {rule_config['condition']}")
        
        # Parse JSONPath and check what it finds
        jsonpath_expr = jsonpath_ng.parse(rule_config['path'])
        matches = jsonpath_expr.find(variant_entry_data)
        print(f"  JSONPath matches: {len(matches)}")
        for match in matches:
            print(f"    Match: value='{match.value}', path='{match.full_path}'")
    
    # Check if the validate_json method transforms the data somehow
    print(f"\nCalling validate_json...")
    result = engine.validate_json(variant_entry_data)
    print(f"Result: {result.is_valid}")
    for error in result.errors:
        print(f"  Error: {error.message} (rule: {error.rule_id})")

if __name__ == "__main__":
    debug_validation_engine_internals()
