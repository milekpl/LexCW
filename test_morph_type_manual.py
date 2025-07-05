#!/usr/bin/env python3
"""
Manual test to check morph-type inheritance behavior
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app import create_app
from app.models import Entry
from app import db
from config import DevelopmentConfig

def test_morph_type_behavior():
    """Test that morph-type respects existing LIFT data"""
    
    app = create_app('development')
    
    with app.app_context():
        # Find an existing entry to test with
        entries = Entry.query.limit(5).all()
        
        print("Testing morph-type behavior:")
        print("=" * 50)
        
        for entry in entries:
            print(f"\nEntry: {entry.lexical_unit}")
            print(f"GUID: {entry.guid}")
            
            # Check current morph-type
            if hasattr(entry, 'grammatical_info') and entry.grammatical_info:
                if isinstance(entry.grammatical_info, str):
                    print(f"Grammatical info (string): {entry.grammatical_info}")
                else:
                    print(f"Grammatical info: {entry.grammatical_info}")
                    
                    morph_type = entry.grammatical_info.get('morph_type', '') if isinstance(entry.grammatical_info, dict) else ''
                    pos = entry.grammatical_info.get('part_of_speech', '') if isinstance(entry.grammatical_info, dict) else ''
                    
                    print(f"Current morph-type: '{morph_type}'")
                    print(f"Current POS: '{pos}'")
                    
                    if morph_type:
                        print("✓ Has existing morph-type from LIFT - should NOT be auto-overridden")
                    else:
                        print("✗ No morph-type - CAN be auto-classified")
            else:
                print("No grammatical info")
                
            print(f"Edit URL: http://localhost:5000/entries/{entry.id}/edit")

if __name__ == "__main__":
    test_morph_type_behavior()
