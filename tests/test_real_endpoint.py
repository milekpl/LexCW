#!/usr/bin/env python3
"""
Test the real edit_entry endpoint with comprehensive debugging
"""

import requests
import json

def test_real_edit_entry():
    """Test the actual edit_entry endpoint with the problematic data"""
    
    url = "http://127.0.0.1:5000/entries/Protestantism_b97495fb-d52f-4755-94bf-a7a762339605/edit"
    
    # This mirrors exactly what the frontend JavaScript sends
    json_data = {
        "lexical_unit": {
            "en": "Protestantism"
        },
        "grammatical_info": {
            "part_of_speech": "Noun"
        },
        "notes": {
            "general": {
                "en": "Test with nested grammatical_info"
            }
        }
    }
    
    print("=== Testing Real Edit Entry Endpoint ===")
    print(f"URL: {url}")
    print(f"Sending JSON: {json.dumps(json_data, indent=2)}")
    
    try:
        headers = {'Content-Type': 'application/json'}
        response = requests.post(url, json=json_data, headers=headers)
        
        print(f"\nResponse Status: {response.status_code}")
        print(f"Response Headers: {dict(response.headers)}")
        print(f"Response Text: {response.text}")
        
        if response.status_code == 200:
            print("✅ SUCCESS: Entry updated successfully")
        elif response.status_code == 302:
            print("⚠️  REDIRECT: Likely an error occurred, check Flask logs")
        else:
            print(f"❌ FAILURE: Status {response.status_code}")
            
    except Exception as e:
        print(f"❌ ERROR: {e}")

if __name__ == "__main__":
    test_real_edit_entry()
