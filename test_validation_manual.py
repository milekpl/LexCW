#!/usr/bin/env python
"""Manual test script for validation relaxation."""

import sys
import os

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.services.validation_engine import ValidationEngine

def test_empty_source_definition():
    """Test that entries with only target language definitions are allowed."""
    engine = ValidationEngine()
    
    entry_data = {
        "id": "test_entry_pl_only",
        "lexical_unit": {"en": "test word"},  # English is source
        "senses": [
            {
                "id": "sense1",
                "definition": {
                    "pl": "test definition in Polish",
                    # No "en" definition - should be allowed
                }
            }
        ]
    }
    
    print("Testing entry with only Polish (target) definition...")
    result = engine.validate_entry(entry_data)

    
    r212_errors = [e for e in result.errors if e.rule_id == 'R2.1.2']
    
    print(f"Total validation errors: {len(result.errors)}")
    print(f"R2.1.2 errors: {len(r212_errors)}")
    
    if r212_errors:
        print("\nR2.1.2 Errors found (UNEXPECTED):")
        for error in r212_errors:
            print(f"  - {error.message} at {error.path}")
        return False
    else:
        print("\n✓ No R2.1.2 errors - validation correctly allows empty source definition!")
        return True

def test_no_definitions():
    """Test that entries with NO definitions are still rejected."""
    engine = ValidationEngine()
    
    entry_data = {
        "id": "test_entry_no_def",
        "lexical_unit": {"en": "test word"},
        "senses": [
            {
                "id": "sense1",
                "definition": {}  # No definitions at all
            }
        ]
    }
    
    print("\n\nTesting entry with NO definitions...")
    result = engine.validate_entry(entry_data)

    
    r212_errors = [e for e in result.errors if e.rule_id == 'R2.1.2']
    
    print(f"Total validation errors: {len(result.errors)}")
    print(f"R2.1.2 errors: {len(r212_errors)}")
    
    if r212_errors:
        print("\n✓ R2.1.2 error found as expected - validation correctly rejects entries with no definitions!")
        for error in r212_errors:
            print(f"  - {error.message} at {error.path}")
        return True
    else:
        print("\n✗ No R2.1.2 errors (UNEXPECTED) - should reject entries with no definitions!")
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("Manual Validation Relaxation Test")
    print("=" * 60)
    
    test1_passed = test_empty_source_definition()
    test2_passed = test_no_definitions()
    
    print("\n" + "=" * 60)
    print("Results:")
    print(f"  Test 1 (Empty source definition allowed): {'PASS' if test1_passed else 'FAIL'}")
    print(f"  Test 2 (No definitions rejected): {'PASS' if test2_passed else 'FAIL'}")
    print("=" * 60)
    
    sys.exit(0 if (test1_passed and test2_passed) else 1)
