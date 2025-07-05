#!/usr/bin/env python3
"""
Comprehensive test for edit_entry functionality.
Tests various scenarios including JSON, form data, and edge cases.
"""

import requests
import json

BASE_URL = "http://127.0.0.1:5000"
ENTRY_ID = "Protestantism_b97495fb-d52f-4755-94bf-a7a762339605"

def test_json_submission():
    """Test JSON submission with dot notation."""
    print("=== Testing JSON Submission ===")
    
    url = f"{BASE_URL}/entries/{ENTRY_ID}/edit"
    
    data = {
        "lexical_unit": {"en": "Protestantism", "pt": "Protestantismo"},
        "grammatical_info.part_of_speech": "Noun",
        "notes": {
            "general": {
                "en": "JSON test note",
                "pt": "Nota de teste JSON"
            }
        }
    }
    
    headers = {"Content-Type": "application/json"}
    
    try:
        response = requests.post(url, json=data, headers=headers)
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text}")
        
        if response.status_code == 200:
            print("✅ JSON submission successful")
        else:
            print("❌ JSON submission failed")
            
    except Exception as e:
        print(f"❌ JSON submission error: {e}")


def test_form_submission():
    """Test HTML form submission with dot notation."""
    print("\n=== Testing Form Submission ===")
    
    url = f"{BASE_URL}/entries/{ENTRY_ID}/edit"
    
    # Form data with dot notation (as sent by browsers)
    form_data = {
        'lexical_unit[en]': 'Protestantism',
        'lexical_unit[pt]': 'Protestantismo',
        'grammatical_info.part_of_speech': 'Noun',
        'notes[general][en]': 'Form test note',
        'notes[general][pt]': 'Nota de teste formulário',
    }
    
    try:
        response = requests.post(url, data=form_data)
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text}")
        
        if response.status_code == 200:
            print("✅ Form submission successful")
        else:
            print("❌ Form submission failed")
            
    except Exception as e:
        print(f"❌ Form submission error: {e}")


def test_empty_submission():
    """Test handling of empty submissions."""
    print("\n=== Testing Empty Submission ===")
    
    url = f"{BASE_URL}/entries/{ENTRY_ID}/edit"
    
    try:
        # Send completely empty POST
        response = requests.post(url)
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text}")
        
        if response.status_code == 400:
            print("✅ Empty submission properly rejected")
        else:
            print("❌ Empty submission handling unexpected")
            
    except Exception as e:
        print(f"❌ Empty submission error: {e}")


def test_malformed_json():
    """Test handling of malformed JSON."""
    print("\n=== Testing Malformed JSON ===")
    
    url = f"{BASE_URL}/entries/{ENTRY_ID}/edit"
    
    try:
        # Send malformed JSON that should fallback to form processing
        headers = {"Content-Type": "application/json"}
        malformed_json = '{"lexical_unit": "test", invalid}'
        
        response = requests.post(url, data=malformed_json, headers=headers)
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text}")
        
        # Should either handle gracefully or reject with 400
        if response.status_code in [200, 400]:
            print("✅ Malformed JSON handled appropriately")
        else:
            print("❌ Malformed JSON handling unexpected")
            
    except Exception as e:
        print(f"❌ Malformed JSON error: {e}")


def main():
    """Run all tests."""
    print("Testing edit_entry function comprehensively...")
    print(f"Target entry: {ENTRY_ID}")
    
    test_json_submission()
    test_form_submission()
    test_empty_submission()
    test_malformed_json()
    
    print("\n=== Test Summary ===")
    print("All tests completed. Check results above.")


if __name__ == "__main__":
    main()
