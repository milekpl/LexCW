#!/usr/bin/env python3
"""
Test the Scholastic Assessment Test entry validation to see what's blocking editing.
"""

import sys
import os
sys.path.insert(0, os.path.abspath('.'))

from app.services.validation_engine import ValidationEngine

def test_scholastic_assessment_test_entry():
    """Test the problematic entry to see what validation errors are blocking editing."""
    
    # Reconstruct the entry data based on the LIFT structure
    entry_data = {
        "id": "Scholastic Assessment Test_25645cb1-c7de-4560-be73-9505d9e9c33f",
        "lexical_unit": {"en": "Scholastic Assessment Test"},
        "morph_type": "phrase",
        "custom_fields": {
            "import-residue": {
                "en": "This was automatically created to satisfy a Lexical Relation, and it should be checked."
            }
        },
        "senses": [
            {
                "id": "99687ebf-29a7-48e5-8d15-90af275d3e09",
                "custom_fields": {
                    "import-residue": {
                        "en": "This was automatically created to satisfy a Lexical Relation, and it should be checked."
                    }
                },
                "relations": [
                    {
                        "type": "skrot",
                        "ref": "7b8be31e-4fd1-4fd2-bb27-dacf7eb75dfc"
                    }
                ]
                # Note: No definition or gloss - this is the problem!
            }
        ]
    }
    
    print("Testing Scholastic Assessment Test entry validation:")
    print("=" * 60)
    
    engine = ValidationEngine()
    result = engine.validate_json(entry_data)
    
    print(f"Valid: {result.is_valid}")
    
    if not result.is_valid:
        print(f"\nCRITICAL ERRORS ({len(result.errors)}):")
        for error in result.errors:
            print(f"  - {error.message} (rule: {error.rule_id})")
    
    if result.warnings:
        print(f"\nWARNINGS ({len(result.warnings)}):")
        for warning in result.warnings:
            print(f"  - {warning.message} (rule: {warning.rule_id})")
    
    if result.info:
        print(f"\nINFO ({len(result.info)}):")
        for info in result.info:
            print(f"  - {info.message} (rule: {info.rule_id})")
    
    print("\n" + "=" * 60)
    print("ISSUE: This entry has validation errors but SHOULD BE EDITABLE!")
    print("Lexicographers NEED to fix invalid entries like this!")
    print("The validation should not BLOCK editing - it should GUIDE editing!")

if __name__ == "__main__":
    test_scholastic_assessment_test_entry()
