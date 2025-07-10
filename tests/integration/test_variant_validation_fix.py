"""
Quick test to verify the variant entry validation fix.
"""
from app.services.validation_engine import ValidationEngine

import pytest

@pytest.mark.integration
def test_variant_entry_validation():
    """Test that variant entries don't trigger false validation errors."""
    
    # Create a variant entry (has _component-lexeme relation but no sense definitions)
    variant_entry_data = {
        "id": "test_variant_entry",
        "lexical_unit": {"seh": "testando"},
        "relations": [
            {
                "type": "_component-lexeme",
                "ref": "base_entry_id",
                "traits": {"variant-type": "Unspecified Variant"}
            }
        ],
        "senses": [
            {
                # Empty sense - should be OK for variant entries
            }
        ]
    }
    
    # Create a regular entry (no _component-lexeme relation, should require definitions)
    regular_entry_data = {
        "id": "test_regular_entry", 
        "lexical_unit": {"seh": "regular"},
        "senses": [
            {
                # Empty sense - should be flagged as error for regular entries
            }
        ]
    }
    
    engine = ValidationEngine()
    
    # Test variant entry - should pass validation
    result1 = engine.validate_json(variant_entry_data)
    print(f"Variant entry validation - Valid: {result1.is_valid}")
    if not result1.is_valid:
        for error in result1.errors:
            print(f"  Error: {error.message}")
    
    # Test regular entry - should fail validation (sense needs definition)
    result2 = engine.validate_json(regular_entry_data)
    print(f"Regular entry validation - Valid: {result2.is_valid}")
    if not result2.is_valid:
        for error in result2.errors:
            print(f"  Error: {error.message}")
    
    return result1.is_valid and not result2.is_valid

if __name__ == "__main__":
    success = test_variant_entry_validation()
    print(f"\nTest {'PASSED' if success else 'FAILED'}")
