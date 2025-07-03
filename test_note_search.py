#!/usr/bin/env python3
"""Test corrected search functionality."""

import requests

def test_search():
    base_url = "http://localhost:5000/api/search/"
    
    tests = [
        ("OMOWNE", "note"),
        ("EXAMPLE", "note"),
        ("test", "lexical_unit"),
    ]
    
    for query, field in tests:
        print(f"\n=== Testing '{query}' in field '{field}' ===")
        try:
            url = f"{base_url}?q={query}&fields={field}"
            response = requests.get(url)
            print(f"Status: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                print(f"Total results: {result['total']}")
                print(f"Fields searched: {result['fields']}")
                for entry in result['entries'][:2]:  # Show first 2
                    print(f"  Entry: {entry['lexical_unit']}")
            else:
                print(f"Error: {response.text}")
                
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    test_search()
