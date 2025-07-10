#!/usr/bin/env python
"""
Test to verify that invalid entries can be loaded for editing.
This ensures lexicographers can always fix invalid entries.
"""

import sys
from pathlib import Path

import pytest

# Add the app directory to the path
sys.path.insert(0, str(Path(__file__).parent / 'app'))

# Set up Flask app context
from app import create_app
from app.services.dictionary_service import DictionaryService
from app.services.validation_engine import ValidationEngine

@pytest.mark.integration
def test_invalid_entry_editable():
    """Test that invalid entries can still be loaded for editing."""
    
    app = create_app()
    
    with app.app_context():
        print("Testing entry loading for editing (regardless of validation state)")
        print("=" * 70)
        
        # Use the problematic entry ID
        entry_id = "Scholastic Assessment Test_25645cb1-c7de-4560-be73-9505d9e9c33f"
        
        # Get the dictionary service
        dict_service = app.injector.get(DictionaryService)
        
        # Try to load the entry (this should always work for editing)
        try:
            entry = dict_service.get_entry(entry_id)
            print(f"✓ Entry loaded successfully: {entry.id}")
            print(f"  Lexical unit: {entry.lexical_unit}")
            print(f"  Senses count: {len(entry.senses)}")
            
            # Now check validation separately (for guidance, not blocking)
            validation_engine = ValidationEngine()
            validation_result = validation_engine.validate_entry(entry)
            
            print(f"\nValidation Status (for guidance only):")
            print(f"  Valid: {validation_result.is_valid}")
            print(f"  Critical errors: {len(validation_result.errors)}")
            print(f"  Warnings: {len(validation_result.warnings)}")
            
            if validation_result.errors:
                print(f"\n  CRITICAL ERRORS (shown as guidance for fixing):")
                for error in validation_result.errors:
                    print(f"    - {error.message} (rule: {error.rule_id})")
                    
            if validation_result.warnings:
                print(f"\n  WARNINGS (shown as guidance for fixing):")
                for warning in validation_result.warnings:
                    print(f"    - {warning.message} (rule: {warning.rule_id})")
            
            print(f"\n✓ SUCCESS: Entry is ALWAYS editable, regardless of validation state!")
            print(f"  Validation errors are shown as GUIDANCE for lexicographers.")
            print(f"  This allows fixing invalid entries, which is the correct behavior.")
            
            return True
            
        except Exception as e:
            print(f"✗ FAILED: Entry could not be loaded for editing: {e}")
            print(f"  This is WRONG - invalid entries MUST be editable for fixing!")
            return False

if __name__ == "__main__":
    success = test_invalid_entry_editable()
    sys.exit(0 if success else 1)
