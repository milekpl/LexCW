#!/usr/bin/env python3
"""Debug routes registration and test validation endpoint."""

import sys
import os
import json
sys.path.insert(0, os.path.abspath("."))

from app import create_app

def check_routes():
    """Check which routes are registered."""
    app = create_app("testing")
    
    print("All registered routes:")
    for rule in app.url_map.iter_rules():
        print(f"  {rule.rule} -> {rule.endpoint} ({', '.join(rule.methods or [])})")
    
    print("\nValidation routes:")
    for rule in app.url_map.iter_rules():
        if 'validation' in rule.rule:
            print(f"  {rule.rule} -> {rule.endpoint} ({', '.join(rule.methods or [])})")
    
    # Test the validation endpoint directly
    print("\nTesting validation endpoint...")
    with app.test_client() as client:
        valid_entry_data = {
            "id": "validation_test",
            "lexical_unit": {
                "en": "valid_word",
                "pl": "poprawne_słowo"
            },
            "senses": [
                {
                    "id": "valid_sense",
                    "gloss": "Valid gloss",
                    "definition": "Valid definition"
                }
            ]
        }
        
        response = client.post('/api/validation/check',
                             data=json.dumps(valid_entry_data),
                             content_type='application/json')
        print(f"Validation endpoint response: {response.status_code}")
        print(f"Response data: {response.get_data(as_text=True)}")

if __name__ == "__main__":
    check_routes()
