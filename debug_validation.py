#!/usr/bin/env python3
"""
Debug script to test the exact validation that's failing
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.services.dictionary_service import DictionaryService
from app.services.validation_engine import ValidationEngine
from app import create_app
from injector import Injector

def debug_validation():
    """Debug the validation of the AIDS test entry"""
    
    app = create_app()
    
    with app.app_context():
        injector = app.injector
        dict_service = injector.get(DictionaryService)
        validation_engine = injector.get(ValidationEngine)
        
        # Get the specific entry
        entry_id = "AIDS test_a774b9c4-c013-4f54-9017-cf818791080c"
        
        try:
            entry = dict_service.get_entry(entry_id)
            
            print("=== ORIGINAL ENTRY STRUCTURE ===")
            print(f"Entry ID: {entry.id}")
            print(f"Entry senses: {len(entry.senses)}")
            
            # Convert to dict like validation does
            entry_dict = entry.to_dict()
            
            print("\n=== ENTRY DICT FOR VALIDATION ===")
            print(f"Entry dict keys: {list(entry_dict.keys())}")
            
            senses = entry_dict.get('senses', [])
            print(f"Senses in dict: {len(senses)}")
            
            for i, sense in enumerate(senses):
                print(f"\nSense {i} dict:")
                print(f"  Keys: {list(sense.keys())}")
                print(f"  definition: '{sense.get('definition', 'NOT_FOUND')}'")
                print(f"  definitions: {sense.get('definitions', 'NOT_FOUND')}")
                print(f"  gloss: '{sense.get('gloss', 'NOT_FOUND')}'")
                print(f"  glosses: {sense.get('glosses', 'NOT_FOUND')}")
                print(f"  variant_of: '{sense.get('variant_of', 'NOT_FOUND')}'")
                
                # Test the validation logic
                has_definition = bool(sense.get('definition', '').strip())
                has_gloss = bool(sense.get('gloss', '').strip())
                has_variant_ref = bool(sense.get('variant_of', '').strip())
                is_variant_sense = bool(sense.get('is_variant', False))
                
                print(f"  Validation checks:")
                print(f"    has_definition: {has_definition}")
                print(f"    has_gloss: {has_gloss}")
                print(f"    has_variant_ref: {has_variant_ref}")
                print(f"    is_variant_sense: {is_variant_sense}")
                print(f"    Should pass: {has_definition or has_gloss or has_variant_ref or is_variant_sense}")
            
            # Now run actual validation
            print("\n=== ACTUAL VALIDATION ===")
            validation_result = validation_engine.validate_entry(entry)
            
            print(f"Validation errors: {len(validation_result.errors)}")
            for error in validation_result.errors:
                print(f"  - {error.message} (Rule: {error.rule_id})")
                
        except Exception as e:
            print(f"Error: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    debug_validation()
