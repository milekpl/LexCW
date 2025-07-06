#!/usr/bin/env python3
"""
Test refactored models with centralized validation system.

This script tests that the refactored Entry and Sense models
properly integrate with the centralized validation system.
"""

import sys
import os

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath('.'))

from app.models.entry import Entry
from app.models.sense import Sense
from app.utils.exceptions import ValidationError


def test_entry_validation_integration():
    """Test that Entry model integrates with centralized validation."""
    print("Testing Entry model validation integration...")
    
    # Test 1: Valid entry should pass
    try:
        valid_entry = Entry(
            id_='test_entry_1',
            lexical_unit={'pl': 'mutu'},
            senses=[{
                'id': 'sense_1',
                'definition': 'A person'
            }]
        )
        result = valid_entry.validate()
        print("✓ Valid entry passed validation")
        
    except Exception as e:
        print(f"✗ Valid entry failed validation: {e}")
        return False
    
    # Test 2: Invalid entry should fail (empty ID)
    try:
        invalid_entry = Entry(
            id_='',  # Empty ID should fail validation
            lexical_unit={'pl': 'mutu'},
            senses=[{
                'id': 'sense_1',
                'definition': 'A person'
            }]
        )
        invalid_entry.validate()
        print("✗ Invalid entry (empty ID) passed validation when it should have failed")
        return False
        
    except ValidationError as e:
        print("✓ Invalid entry (empty ID) correctly failed validation")
        
    except Exception as e:
        print(f"✗ Unexpected error during validation: {e}")
        return False
    
    # Test 3: Invalid entry should fail (missing senses)
    try:
        invalid_entry = Entry(
            id_='test_entry_2',
            lexical_unit={'pl': 'mutu'},
            senses=[]
        )
        invalid_entry.validate()
        print("✗ Invalid entry (no senses) passed validation when it should have failed")
        return False
        
    except ValidationError as e:
        print("✓ Invalid entry (no senses) correctly failed validation")
        
    except Exception as e:
        print(f"✗ Unexpected error during validation: {e}")
        return False
    
    return True


def test_sense_validation_integration():
    """Test that Sense model integrates with centralized validation."""
    print("\nTesting Sense model validation integration...")
    
    # Test 1: Valid sense should pass
    try:
        valid_sense = Sense(
            id_='sense_1',
            definition='A person'
        )
        result = valid_sense.validate()
        print("✓ Valid sense passed validation")
        
    except Exception as e:
        print(f"✗ Valid sense failed validation: {e}")
        return False
    
    # Test 2: Invalid sense should fail (empty ID)
    try:
        invalid_sense = Sense(
            id_='',  # Empty ID should fail validation
            definition='A person'
        )
        invalid_sense.validate()
        print("✗ Invalid sense (empty ID) passed validation when it should have failed")
        return False
        
    except ValidationError as e:
        print("✓ Invalid sense (empty ID) correctly failed validation")
        
    except Exception as e:
        print(f"✗ Unexpected error during validation: {e}")
        return False
    
    return True


def test_centralized_validation_consistency():
    """Test that validation results are consistent between models and engine."""
    print("\nTesting validation consistency...")
    
    from app.services.validation_engine import ValidationEngine
    
    engine = ValidationEngine()
    
    # Create test entry data
    entry_data = {
        'id': 'test_entry_3',
        'lexical_unit': {'pl': 'mutu'},
        'senses': [{
            'id': 'sense_1',
            'definition': 'A person'
        }]
    }
    
    # Test direct engine validation
    try:
        engine_result = engine.validate_json(entry_data)
        print(f"✓ Engine validation completed. Valid: {engine_result.is_valid}")
    except Exception as e:
        print(f"✗ Engine validation failed: {e}")
        return False
    
    # Test model validation
    try:
        entry = Entry(**entry_data)
        model_result = entry.validate()
        print(f"✓ Model validation completed. Valid: {model_result}")
    except ValidationError as e:
        print(f"✗ Model validation failed: {e}")
        return False
    except Exception as e:
        print(f"✗ Unexpected error in model validation: {e}")
        return False
    
    # Both should give consistent results for valid data
    if engine_result.is_valid == model_result:
        print("✓ Engine and model validation results are consistent")
        return True
    else:
        print("✗ Engine and model validation results are inconsistent")
        return False


def main():
    """Run all integration tests."""
    print("=" * 60)
    print("CENTRALIZED VALIDATION MODEL INTEGRATION TESTS")
    print("=" * 60)
    
    all_passed = True
    
    # Run tests
    all_passed &= test_entry_validation_integration()
    all_passed &= test_sense_validation_integration()
    all_passed &= test_centralized_validation_consistency()
    
    print("\n" + "=" * 60)
    if all_passed:
        print("✓ ALL INTEGRATION TESTS PASSED")
        print("\nThe refactored models successfully integrate with the centralized validation system!")
    else:
        print("✗ SOME TESTS FAILED")
        print("\nPlease check the errors above and fix the integration issues.")
    print("=" * 60)
    
    return 0 if all_passed else 1


if __name__ == '__main__':
    exit(main())
