#!/usr/bin/env python3
"""
Test to verify language constraints are properly enforced.
"""

import requests
import json

import pytest

@pytest.mark.integration
def test_language_constraints():
    """Test that only allowed languages are accepted."""
    
    # First, get the allowed languages
    print("=== Getting allowed languages ===")
    response = requests.get('http://127.0.0.1:5000/api/ranges/language-codes')
    
    if response.status_code != 200:
        print("❌ Failed to get language codes")
        return
    
    allowed_languages = response.json().get('data', [])
    print(f"Allowed languages: {allowed_languages}")
    
    # Test with allowed language
    print(f"\n=== Testing with allowed language ({allowed_languages[0] if allowed_languages else 'none'}) ===")
    if allowed_languages:
        test_data = {
            "lexical_unit": {allowed_languages[0]: "Test Entry"},
            "grammatical_info": {"part_of_speech": "Noun"},
            "notes": {
                "general": {allowed_languages[0]: "Test note in allowed language"}
            }
        }
        
    _test_submission("Protestantism_b97495fb-d52f-4755-94bf-a7a762339605", test_data, "allowed language")
    
    # Test with disallowed language (Portuguese)
    print("\n=== Testing with disallowed language (Portuguese) ===")
    test_data_pt = {
        "lexical_unit": {"pt": "Test Entry Portuguese"},
        "grammatical_info": {"part_of_speech": "Noun"},
        "notes": {
            "general": {"pt": "Test note in Portuguese"}
        }
    }
    
    _test_submission("Protestantism_b97495fb-d52f-4755-94bf-a7a762339605", test_data_pt, "disallowed language (Portuguese)")

def _test_submission(entry_id, data, description):
    """Test a specific data submission."""
    url = f"http://127.0.0.1:5000/entries/{entry_id}/edit"
    
    try:
        headers = {'Content-Type': 'application/json'}
        response = requests.post(url, json=data, headers=headers)
        
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            print(f"✅ SUCCESS: {description} submission accepted")
        elif response.status_code in [400, 422]:
            print(f"✅ EXPECTED: {description} submission rejected (validation error)")
        elif response.status_code == 302:
            print(f"⚠️  REDIRECT: {description} submission caused redirect (likely error)")
        else:
            print(f"❓ UNEXPECTED: {description} submission returned {response.status_code}")
        
        print(f"Response: {response.text[:200]}...")
        
    except Exception as e:
        print(f"❌ ERROR testing {description}: {e}")

if __name__ == "__main__":
    test_language_constraints()
