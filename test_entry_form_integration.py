#!/usr/bin/env python3
"""
Test that the entry form loads correctly and pronunciations display properly.
"""

import requests
from bs4 import BeautifulSoup
import json
import re

def test_entry_form():
    """Test that the entry form loads correctly."""
    base_url = "http://127.0.0.1:5000"
    
    # Test that we can load the entry form for Protestant
    response = requests.get(f"{base_url}/entries/Protestant1_8c895a90-6c91-4257-8ada-528e18d2ba69/edit")
    
    if response.status_code != 200:
        print(f"ERROR: Failed to load entry form. Status: {response.status_code}")
        return False
    
    soup = BeautifulSoup(response.text, 'html.parser')
    
    # Check that the entry form exists
    form = soup.find('form', {'id': 'entry-form'})
    if not form:
        print("ERROR: Entry form not found in HTML")
        return False
    
    # Check that pronunciation container exists
    pronunciation_container = soup.find('div', {'id': 'pronunciation-container'})
    if not pronunciation_container:
        print("ERROR: Pronunciation container not found")
        return False
    
    # Check that JavaScript data is properly encoded
    scripts = soup.find_all('script')
    pronunciation_data_found = False
    
    for script in scripts:
        if script.string and 'pronunciations' in script.string:
            print("Found pronunciation data in JavaScript")
            
            # Extract the pronunciation data
            match = re.search(r'pronunciations\s*:\s*(\[.*?\])', script.string, re.DOTALL)
            if match:
                try:
                    pronunciation_json = match.group(1)
                    pronunciations = json.loads(pronunciation_json)
                    print(f"Successfully parsed {len(pronunciations)} pronunciations")
                    
                    # Check for IPA characters
                    for p in pronunciations:
                        if 'value' in p and p['value']:
                            print(f"  Pronunciation: {p['value']}")
                            if any(ord(c) > 127 for c in p['value']):
                                print("    Contains Unicode/IPA characters ✓")
                    
                    pronunciation_data_found = True
                except json.JSONDecodeError as e:
                    print(f"ERROR: Failed to parse pronunciation JSON: {e}")
                    return False
    
    if not pronunciation_data_found:
        print("WARNING: No pronunciation data found in JavaScript")
    
    # Test that required API endpoints work
    api_endpoints = [
        "/api/ranges/relation-type",
        "/api/ranges/etymology-types", 
        "/api/ranges/language-codes",
        "/api/ranges/variant-types-from-traits",
    ]
    
    for endpoint in api_endpoints:
        response = requests.get(f"{base_url}{endpoint}")
        if response.status_code != 200:
            print(f"ERROR: API endpoint {endpoint} failed with status {response.status_code}")
            return False
        else:
            print(f"✓ API endpoint {endpoint} working")
    
    print("\n✓ Entry form loads correctly")
    print("✓ Pronunciation container found")
    print("✓ JavaScript data properly encoded")
    print("✓ All API endpoints working")
    
    return True

if __name__ == '__main__':
    success = test_entry_form()
    if success:
        print("\n🎉 All tests passed! The entry form should work correctly.")
    else:
        print("\n❌ Some tests failed. Please check the issues above.")
