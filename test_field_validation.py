#!/usr/bin/env python3
"""Test that invalid 'notes' field is rejected."""

import requests

def test_invalid_field():
    base_url = "http://localhost:5000/api/search/"
    
    print("=== Testing invalid 'notes' field (should return no results) ===")
    try:
        url = f"{base_url}?q=EXAMPLE&fields=notes"  # Invalid field
        response = requests.get(url)
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"Total results: {result['total']}")
            print(f"Fields searched: {result['fields']}")
            if result['total'] == 0:
                print("✅ Correctly rejected invalid 'notes' field")
            else:
                print("❌ Should not find results with invalid field")
        else:
            print(f"Error: {response.text}")
            
    except Exception as e:
        print(f"Error: {e}")

    print("\n=== Testing valid 'note' field (should return results) ===")
    try:
        url = f"{base_url}?q=EXAMPLE&fields=note"  # Valid field
        response = requests.get(url)
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"Total results: {result['total']}")
            print(f"Fields searched: {result['fields']}")
            if result['total'] > 0:
                print("✅ Correctly found results with valid 'note' field")
            else:
                print("❌ Should find results with valid field")
        else:
            print(f"Error: {response.text}")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_invalid_field()
