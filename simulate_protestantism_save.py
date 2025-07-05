#!/usr/bin/env python3
"""
Script to simulate saving the Protestantism entry and reproduce the error.
"""

import requests
import json

def simulate_form_submission():
    """Simulate the exact form submission that would trigger the error."""
    
    # This simulates adding some data to a field with dot notation
    # which should trigger the problem
    form_data = {
        'lexical_unit': 'Protestantism',
        'grammatical_info.part_of_speech': 'Noun',  # This is the problematic field
        'senses[0].definition': 'Test definition for debugging'
    }
    
    entry_id = 'Protestantism_b97495fb-d52f-4755-94bf-a7a762339605'
    url = f'http://127.0.0.1:5000/entries/{entry_id}/edit'
    
    print(f"Sending POST request to {url}")
    print(f"Form data: {json.dumps(form_data, indent=2)}")
    
    try:
        response = requests.post(url, json=form_data, timeout=10)
        print(f"Response status: {response.status_code}")
        print(f"Response content: {response.text}")
        
        if response.status_code != 200:
            print("ERROR: Request failed!")
        else:
            print("SUCCESS: Request completed")
            
    except Exception as e:
        print(f"ERROR: Request failed with exception: {e}")

if __name__ == "__main__":
    simulate_form_submission()
