#!/usr/bin/env python3
"""
Test script to simulate HTML form submission to the edit_entry endpoint
This simulates the browser sending form data (not JSON) with dot notation keys
"""

import requests
import time

import pytest

@pytest.mark.integration
def test_form_submission():
    # URL for editing entry (use the same entry ID from the original working script)
    entry_id = 'Protestantism_b97495fb-d52f-4755-94bf-a7a762339605'
    url = f"http://127.0.0.1:5000/entries/{entry_id}/edit"
    
    # Simulate form data as it would be sent by browser
    # This includes the problematic dot notation keys
    form_data = {
        'lexical_unit[en]': 'Protestantism',
        'lexical_unit[pt]': 'Protestantismo',
        'grammatical_info.part_of_speech': 'Noun',  # This is the problematic key
        'notes[general][en]': 'A form of Christianity',
        'notes[general][pt]': 'Uma forma de Cristianismo',
        'senses[0][definition][en]': 'Christian religious movement',
        'senses[0][definition][pt]': 'Movimento religioso cristão'
    }
    
    print(f"Sending form data to: {url}")
    print(f"Form data: {form_data}")
    
    try:
        # Send POST request with form data (NOT JSON)
        response = requests.post(
            url, 
            data=form_data,  # Use 'data' instead of 'json' to send as form data
            headers={'Content-Type': 'application/x-www-form-urlencoded'}
        )
        
        print(f"Response status: {response.status_code}")
        print(f"Response headers: {dict(response.headers)}")
        print(f"Response text: {response.text}")
        
        if response.status_code == 200:
            print("✅ Form submission successful!")
        else:
            print(f"❌ Form submission failed with status {response.status_code}")
            
    except Exception as e:
        print(f"❌ Error during form submission: {e}")

if __name__ == "__main__":
    test_form_submission()
