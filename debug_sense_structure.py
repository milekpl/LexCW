#!/usr/bin/env python3
"""
Debug script to check the actual structure of sense data being validated
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.services.dictionary_service import DictionaryService
from app import create_app
from injector import Injector

def debug_entry_structure():
    """Debug the actual structure of the AIDS test entry"""
    
    app = create_app()
    
    with app.app_context():
        injector = app.injector
        dict_service = injector.get(DictionaryService)
        
        # Get the specific entry
        entry_id = "AIDS test_a774b9c4-c013-4f54-9017-cf818791080c"
        
        try:
            entry = dict_service.get_entry(entry_id)
            
            print("=== ENTRY STRUCTURE ===")
            print(f"Entry ID: {entry.id}")
            print(f"Lexical Unit: {entry.lexical_unit}")
            
            print(f"\n=== SENSES ({len(entry.senses)}) ===")
            for i, sense in enumerate(entry.senses):
                print(f"\nSense {i}:")
                print(f"  ID: {sense.id}")
                print(f"  Definition: {sense.definition}")
                print(f"  Definition type: {type(sense.definition)}")
                if hasattr(sense, 'gloss'):
                    print(f"  Gloss: {sense.gloss}")
                    print(f"  Gloss type: {type(sense.gloss)}")
                if hasattr(sense, 'variant_of'):
                    print(f"  Variant of: {sense.variant_of}")
                print(f"  All attributes: {vars(sense)}")
                
        except Exception as e:
            print(f"Error getting entry: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    debug_entry_structure()
