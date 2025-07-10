#!/usr/bin/env python3
"""
Test the complete entry creation flow with realistic form data.
"""

import sys
import os
import pytest

sys.path.insert(0, os.path.abspath('.'))

from app import create_app
from app.utils.multilingual_form_processor import merge_form_data_with_entry_data
from app.models.entry import Entry
from app.services.validation_engine import ValidationEngine

@pytest.mark.integration
def test_complete_entry_flow():
    """Test the complete entry creation flow as it happens in the view."""
    print("=== Testing Complete Entry Creation Flow ===")
    
    # Simulate realistic form data (as it would come from the frontend)
    form_data = {
        'lexical_unit': 'testword',
        'senses[0].definition': 'Test definition',
        'senses[0].gloss': 'Test gloss',
        'morph_type': 'stem'
    }
    
    print(f"1. Original form data: {form_data}")
    
    # Step 1: Process form data (as done in add_entry route)
    empty_entry_data = {}
    merged_data = merge_form_data_with_entry_data(form_data, empty_entry_data)
    print(f"2. Merged data: {merged_data}")
    
    # Step 2: Create Entry object (as done in add_entry route)
    entry = Entry.from_dict(merged_data)
    print(f"3. Entry created with ID: {entry.id}")
    print(f"   Entry has {len(entry.senses)} senses")
    if entry.senses:
        print(f"   First sense ID: {entry.senses[0].id}")
    
    # Step 3: Validate entry (as done in create_entry in dictionary service)
    print(f"4. Running entry validation...")
    
    app = create_app()
    with app.app_context():
        try:
            validator = ValidationEngine()
            result = validator.validate_entry(entry)
            print(f"   Validation result: is_valid={result.is_valid}")
            print(f"   Errors: {len(result.errors)}")
            print(f"   Warnings: {len(result.warnings)}")
            
            if result.errors:
                print("   Error details:")
                for error in result.errors:
                    print(f"     - {error.rule_id}: {error.message} (path: {error.path})")
            
            # Step 4: Try the model's validate method (as called by create_entry)
            print(f"5. Testing entry.validate() method...")
            try:
                is_valid = entry.validate()
                print(f"   entry.validate() returned: {is_valid}")
            except Exception as e:
                print(f"   entry.validate() failed: {e}")
                
        except Exception as e:
            print(f"   Validation failed with exception: {e}")
            import traceback
            traceback.print_exc()

if __name__ == '__main__':
    test_complete_entry_flow()
