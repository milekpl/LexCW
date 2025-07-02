#!/usr/bin/env python3

"""
Debug script to test validation endpoint.
"""

import json
import sys
import os

# Add app directory to Python path  
sys.path.insert(0, os.path.abspath('.'))

def test_validation_debug():
    """Debug validation issues."""
    
    # Create test data matching what the test uses
    entry_data = {
        'id': 'test',
        'lexical_unit': {'en': 'test'},
        'senses': [{
            'id': 'sense1',
            'glosses': {'en': 'test gloss'}
        }]
    }
    
    print("Testing entry data:", json.dumps(entry_data, indent=2))
    
    # Try to create Entry object directly
    try:
        from app.models.entry import Entry
        entry = Entry.from_dict(entry_data)
        print("Entry created successfully:", entry.id)
        
        # Try validation
        try:
            result = entry.validate()
            print("Validation result:", result)
        except Exception as e:
            print("Validation error:", e)
            if hasattr(e, 'errors'):
                print("Validation errors:", e.errors)
                
    except Exception as e:
        print("Entry creation error:", e)
    
    # Test the endpoint directly
    print("\n--- Testing API endpoint ---")
    try:
        from app import create_app
        app = create_app('testing')
        with app.test_client() as client:
            response = client.post('/api/validation/check',
                                 data=json.dumps(entry_data),
                                 content_type='application/json')
            print("Response status:", response.status_code)
            print("Response data:", response.get_json())
    except Exception as e:
        print("API test error:", e)

if __name__ == '__main__':
    test_validation_debug()
