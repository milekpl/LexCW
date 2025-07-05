#!/usr/bin/env python3
"""
Test the multilingual form processor with the exact JSON structure from frontend
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from app.utils.multilingual_form_processor import merge_form_data_with_entry_data

def test_processor():
    """Test the processor with problematic data"""
    
    # This is exactly what the frontend sends
    frontend_json = {
        "lexical_unit": {
            "en": "Protestantism"
        },
        "grammatical_info": {
            "part_of_speech": "Noun"
        },
        "notes": {
            "general": {
                "en": "A form of Christianity"
            }
        },
        "senses": [
            {
                "definition": {
                    "en": "Christian movement"
                }
            }
        ]
    }
    
    # Existing entry data (simplified)
    existing_data = {
        "id": "test-id",
        "lexical_unit": {"en": "Old Value"},
        "grammatical_info": "Old POS",
        "senses": []
    }
    
    print("=== Testing Multilingual Form Processor ===")
    print(f"Frontend JSON: {frontend_json}")
    print(f"Existing data: {existing_data}")
    
    try:
        result = merge_form_data_with_entry_data(frontend_json, existing_data)
        print(f"\n=== RESULT ===")
        print(f"Merged result: {result}")
        
        if 'grammatical_info' in result:
            gi = result['grammatical_info']
            print(f"\ngrammatical_info: {gi}")
            print(f"grammatical_info type: {type(gi)}")
            print(f"Is string? {isinstance(gi, str)}")
            
            if isinstance(gi, str):
                print("✅ SUCCESS: grammatical_info correctly flattened to string")
            else:
                print("❌ FAILURE: grammatical_info is still a dict")
        
    except Exception as e:
        print(f"❌ ERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_processor()
