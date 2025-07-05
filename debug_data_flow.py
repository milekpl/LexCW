#!/usr/bin/env python3
"""
Debug the exact data flow and serialization issue with entry saving.
"""

import requests
import json

def test_and_debug_data_flow():
    """Test form submission and debug the data that's created."""
    print("=== Debugging Form Data Processing ===")
    
    url = "http://127.0.0.1:5000/entries/Protestantism_b97495fb-d52f-4755-94bf-a7a762339605/edit"
    
    # Minimal form data that should work
    form_data = {
        'lexical_unit[en]': 'Protestantism',
        'grammatical_info.part_of_speech': 'Noun',
        'senses[0][definition][en]': 'A Christian religious movement',
    }
    
    print(f"Sending minimal form data to: {url}")
    print("Form data:")
    for key, value in form_data.items():
        print(f"  {key}: {value}")
    
    try:
        response = requests.post(url, data=form_data)
        print(f"\nResponse Status: {response.status_code}")
        print(f"Response: {response.text}")
        
        if response.status_code != 200:
            print("❌ Request failed - checking logs for clues...")
        else:
            print("✅ Request succeeded")
            
    except Exception as e:
        print(f"❌ Error during test: {e}")

def test_json_data_flow():
    """Test equivalent JSON data."""
    print("\n=== Testing JSON Data Flow ===")
    
    url = "http://127.0.0.1:5000/entries/Protestantism_b97495fb-d52f-4755-94bf-a7a762339605/edit"
    
    # Equivalent JSON data
    json_data = {
        "lexical_unit": {"en": "Protestantism"},
        "grammatical_info": "Noun",  # Note: not nested, just a string
        "senses": [
            {
                "definition": {"en": "A Christian religious movement"}
            }
        ]
    }
    
    print("Sending equivalent JSON data:")
    print(json.dumps(json_data, indent=2))
    
    try:
        headers = {'Content-Type': 'application/json'}
        response = requests.post(url, json=json_data, headers=headers)
        print(f"\nJSON Response Status: {response.status_code}")
        print(f"JSON Response: {response.text}")
        
        if response.status_code != 200:
            print("❌ JSON request also failed")
        else:
            print("✅ JSON request succeeded")
            
    except Exception as e:
        print(f"❌ JSON test error: {e}")

def main():
    """Run debug tests."""
    print("DEBUGGING DATA FLOW ISSUE")
    print("=" * 50)
    
    test_and_debug_data_flow()
    test_json_data_flow()

if __name__ == "__main__":
    main()
