#!/usr/bin/env python3
"""
Complete test for variant entry validation fix.
This test verifies that variant entries don't require senses and can be saved.
"""

import sys
import os
import pytest

sys.path.insert(0, os.path.abspath('.'))

from app.services.validation_engine import ValidationEngine
from app.models.entry import Entry

@pytest.mark.integration
def test_variant_entry_without_senses():
    """Test that a variant entry without senses passes validation."""
    
    # Create a variant entry (has _component-lexeme relation with variant-type trait)
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
        # No senses field at all - should be OK for variant entries
    }
    
    engine = ValidationEngine()
    
    # Test validation engine directly
    result = engine.validate_json(variant_entry_data)
    print(f"Variant entry validation via engine - Valid: {result.is_valid}")
    if not result.is_valid:
        for error in result.errors:
            print(f"  Error: {error.message}")
    
    assert result.is_valid, "Variant entry should pass validation even without senses"
    
    # Test Entry model validation
    try:
        entry = Entry(**variant_entry_data)
        entry_valid = entry.validate()
        print(f"Variant entry validation via model - Valid: {entry_valid}")
        assert entry_valid, "Variant entry should pass model validation"
    except Exception as e:
        print(f"Variant entry model validation failed: {e}")
        assert False, f"Variant entry model validation should pass: {e}"

@pytest.mark.integration
def test_regular_entry_requires_senses():
    """Test that a regular entry without senses fails validation."""
    
    # Create a regular entry (no _component-lexeme relation)
    regular_entry_data = {
        "id": "test_regular_entry", 
        "lexical_unit": {"pl": "regular"}
        # No senses field - should fail for regular entries
    }
    
    engine = ValidationEngine()
    
    # Test validation engine directly
    result = engine.validate_json(regular_entry_data)
    print(f"Regular entry validation - Valid: {result.is_valid}")
    if not result.is_valid:
        for error in result.errors:
            print(f"  Error: {error.message}")
    
    assert not result.is_valid, "Regular entry should fail validation without senses"
    assert any("at least one sense" in error.message.lower() for error in result.errors), "Should have sense requirement error"

@pytest.mark.integration
def test_variant_entry_with_senses():
    """Test that a variant entry with senses also passes validation."""
    
    # Create a variant entry with senses (should still be valid)
    variant_entry_data = {
        "id": "test_variant_entry_with_senses",
        "lexical_unit": {"pl": "testando"},
        "relations": [
            {
                "type": "_component-lexeme",
                "ref": "base_entry_id",
                "traits": {"variant-type": "Unspecified Variant"}
            }
        ],
        "senses": [
            {
                "id": "sense_1",
                "definition": {"en": "A variant form"}
            }
        ]
    }
    
    engine = ValidationEngine()
    result = engine.validate_json(variant_entry_data)
    print(f"Variant entry with senses validation - Valid: {result.is_valid}")
    if not result.is_valid:
        for error in result.errors:
            print(f"  Error: {error.message}")
    
    assert result.is_valid, "Variant entry with senses should also pass validation"

@pytest.mark.integration
def test_non_variant_relation_requires_senses():
    """Test that entries with non-variant relations still require senses."""
    
    # Create an entry with relations but not variant type
    entry_data = {
        "id": "test_non_variant_relation",
        "lexical_unit": {"pl": "related"},
        "relations": [
            {
                "type": "_component-lexeme",
                "ref": "base_entry_id"
                # No variant-type trait - not a variant
            }
        ]
        # No senses field - should fail
    }
    
    engine = ValidationEngine()
    result = engine.validate_json(entry_data)
    print(f"Non-variant relation entry validation - Valid: {result.is_valid}")
    if not result.is_valid:
        for error in result.errors:
            print(f"  Error: {error.message}")
    
    assert not result.is_valid, "Entry with non-variant relation should fail validation without senses"

if __name__ == "__main__":
    print("=" * 60)
    print("VARIANT ENTRY VALIDATION COMPLETE TEST")
    print("=" * 60)
    
    try:
        test_variant_entry_without_senses()
        print("✓ Test 1 passed: Variant entry without senses")
        
        test_regular_entry_requires_senses()
        print("✓ Test 2 passed: Regular entry requires senses")
        
        test_variant_entry_with_senses()
        print("✓ Test 3 passed: Variant entry with senses")
        
        test_non_variant_relation_requires_senses()
        print("✓ Test 4 passed: Non-variant relation requires senses")
        
        print("\n" + "=" * 60)
        print("✓ ALL VARIANT ENTRY TESTS PASSED")
        print("Variant entries are correctly exempted from sense requirements!")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n✗ TEST FAILED: {e}")
        sys.exit(1)
