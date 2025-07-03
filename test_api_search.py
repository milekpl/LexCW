#!/usr/bin/env python3
"""Test API search functionality."""

import requests

def test_api_search():
    base_url = "http://localhost:5000/api/search/"
    
    tests = [
        {
            "name": "Search for EXAMPLE in all fields",
            "url": f"{base_url}?q=EXAMPLE",
        },
        {
            "name": "Search for EXAMPLE_TRANSLATION in notes only",
            "url": f"{base_url}?q=EXAMPLE_TRANSLATION&fields=notes",
        },
        {
            "name": "Search for EXAMPLE_TRANSLATION in all fields",
            "url": f"{base_url}?q=EXAMPLE_TRANSLATION",
        },
        {
            "name": "Search for DNA in lexical_unit only",
            "url": f"{base_url}?q=DNA&fields=lexical_unit",
        },
    ]
    
    for test in tests:
        print(f"\n=== {test['name']} ===")
        try:
            response = requests.get(test["url"])
            print(f"Status: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                print(f"Total results: {result['total']}")
                print(f"Fields searched: {result['fields']}")
                
                for i, entry in enumerate(result['entries'][:3]):  # Show first 3
                    print(f"  Entry {i+1}: {entry['lexical_unit']}")
                    if entry.get('notes'):
                        print(f"    Notes: {entry['notes']}")
            else:
                print(f"Error: {response.text}")
                
        except requests.exceptions.ConnectionError:
            print("Error: Could not connect to API server")
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    test_api_search()
