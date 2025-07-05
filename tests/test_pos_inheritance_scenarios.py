#!/usr/bin/env python3
"""
Test script to verify POS inheritance logic works correctly in different scenarios.
"""

import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from app import create_app
from app.services.dictionary_service import DictionaryService

def test_pos_inheritance_scenarios():
    """Test different POS inheritance scenarios."""
    app = create_app()
    
    with app.app_context():
        dict_service = app.injector.get(DictionaryService)
        
        # Test entries with different scenarios
        test_entries = [
            "Protestant2_2db3c121-3b23-428e-820d-37b76e890616",  # All senses should have "Adjective"
        ]
        
        for entry_id in test_entries:
            print(f"\n=== Testing Entry: {entry_id} ===")
            
            entry = dict_service.get_entry(entry_id)
            
            if entry:
                print(f"Lexical unit: {entry.lexical_unit}")
                print(f"Current grammatical_info: '{entry.grammatical_info}'")
                print(f"Number of senses: {len(entry.senses)}")
                
                # Show sense grammatical info
                sense_pos = []
                for i, sense in enumerate(entry.senses):
                    pos = sense.grammatical_info or "None"
                    sense_pos.append(pos)
                    print(f"  Sense {i+1}: grammatical_info='{pos}'")
                
                # Test inheritance logic
                print("\nTesting inheritance logic...")
                
                # Check if all senses agree
                non_empty_pos = [pos for pos in sense_pos if pos and pos.strip() and pos.lower() != 'none']
                unique_pos = list(set(non_empty_pos))
                
                print(f"Non-empty POS values: {non_empty_pos}")
                print(f"Unique POS values: {unique_pos}")
                
                if len(unique_pos) == 1:
                    print(f"✓ All senses agree on POS: '{unique_pos[0]}'")
                    print("→ Entry-level POS should be auto-inherited and NOT required")
                elif len(unique_pos) > 1:
                    print(f"✗ POS discrepancy detected: {unique_pos}")
                    print("→ Entry-level POS should be required for manual selection")
                else:
                    print("⚠ No senses have POS set")
                    print("→ Entry-level POS should be required")
                
                # Apply inheritance and show result
                entry._apply_pos_inheritance()
                print(f"After inheritance: '{entry.grammatical_info}'")
                
            else:
                print("Entry not found!")

if __name__ == "__main__":
    test_pos_inheritance_scenarios()
