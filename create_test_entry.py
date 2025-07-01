#!/usr/bin/env python3
"""
Create a test entry with relations to test the UI.
"""

import requests
import json

def create_test_entry():
    """Create a test entry with relations."""
    
    # Entry data with relations
    entry_data = {
        "id": "ui-test-entry",
        "lexical_unit": {
            "en": "test word",
            "seh": "palavra teste"
        },
        "grammatical_info": "noun",
        "senses": [
            {
                "id": "sense-1",
                "gloss": {"en": "a test", "seh": "um teste"},
                "definition": {"en": "something used for testing", "seh": "algo usado para testar"}
            }
        ],
        "relations": [
            {"type": "synonym", "ref": "similar-word"},
            {"type": "antonym", "ref": "opposite-word"}
        ],
        "etymologies": [
            {
                "type": "borrowing",
                "source": "Latin",
                "form": {"lang": "la", "text": "testum"},
                "gloss": {"lang": "en", "text": "earthen pot"}
            }
        ]
    }
    
    # Send POST request to create entry
    try:
        response = requests.post(
            "http://localhost:5000/api/entries/",
            json=entry_data,
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code == 201:
            print("Test entry created successfully!")
            print("Response:", response.json())
            return True
        else:
            print(f"Failed to create entry. Status: {response.status_code}")
            print("Response:", response.text)
            return False
            
    except Exception as e:
        print(f"Error creating entry: {e}")
        return False

if __name__ == "__main__":
    success = create_test_entry()
    if success:
        print("\nNow you can test editing this entry at:")
        print("http://localhost:5000/entries/ui-test-entry/edit")
    else:
        print("Failed to create test entry")
