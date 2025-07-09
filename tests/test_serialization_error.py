#!/usr/bin/env python3
"""
Test to reproduce the exact error scenario
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from app import create_app, injector
from app.services.dictionary_service import DictionaryService
from app.models.entry import Entry

def test_entry_serialization_issue():
    """Test what happens when we try to update entry with complex data"""
    
    app = create_app()
    
    with app.app_context():
        # Use the app's injector, which should be properly configured
        dict_service = app.injector.get(DictionaryService)

        # Get the problematic entry
        try:
            entry = dict_service.get_entry("Protestantism_b97495fb-d52f-4755-94bf-a7a762339605")
            print(f"✅ Successfully retrieved entry: {entry.id}")
            print(f"Entry type: {type(entry)}")
            print(f"Lexical unit: {entry.lexical_unit} (type: {type(entry.lexical_unit)})")
            print(f"Grammatical info: {entry.grammatical_info} (type: {type(entry.grammatical_info)})")

            # Check for any dict values that shouldn't be dicts
            entry_dict = entry.to_dict()
            print(f"\nEntry dict keys: {list(entry_dict.keys())}")

            for key, value in entry_dict.items():
                if isinstance(value, dict) and key not in ['lexical_unit', 'notes', 'pronunciations', 'custom_fields']:
                    print(f"⚠️ WARNING: {key} is unexpectedly a dict: {value}")

            # Try to validate the entry
            try:
                is_valid = entry.validate()
                print(f"✅ Entry validation: {is_valid}")
            except Exception as e:
                print(f"❌ Entry validation failed: {e}")

            # Try to update the entry (this should trigger the error)
            try:
                dict_service.update_entry(entry)
                print("✅ Entry update successful")
            except Exception as e:
                print(f"❌ Entry update failed: {e}")
                import traceback
                traceback.print_exc()

        except Exception as e:
            print(f"❌ Failed to retrieve entry: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    test_entry_serialization_issue()
