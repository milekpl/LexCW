#!/usr/bin/env python3
"""
Test API endpoints to verify they work correctly.
"""

import requests

def test_api_endpoints():
    """Test the API endpoints."""
    base_url = "http://127.0.0.1:5000"
    
    # Start the server first
    print("Testing API endpoints...")
    
    endpoints = [
        "/api/ranges/relation-type",
        "/api/ranges/etymology-types", 
        "/api/ranges/language-codes",
        "/api/ranges/grammatical-info",
        "/api/ranges/variant-types-from-traits",
    ]
    
    for endpoint in endpoints:
        try:
            response = requests.get(f"{base_url}{endpoint}", timeout=10)
            print(f"{endpoint}: {response.status_code}")
            if response.status_code == 200:
                data = response.json()
                if 'data' in data:
                    print(f"  Data items: {len(data['data'])}")
                elif 'language_codes' in data:
                    print(f"  Language codes: {len(data['language_codes'])}")
                else:
                    print(f"  Keys: {list(data.keys())}")
            else:
                print(f"  Error: {response.text}")
        except Exception as e:
            print(f"{endpoint}: ERROR - {e}")
    
    print("\nTesting alternative API routes...")
    
    alt_endpoints = [
        "/api/ranges/relation-types",
        "/api/ranges/etymology-types", 
        "/api/ranges/grammatical-info",
        "/api/ranges/variant-types-from-traits",
        "/api/ranges/language-codes",
    ]
    
    for endpoint in alt_endpoints:
        try:
            response = requests.get(f"{base_url}{endpoint}", timeout=10)
            print(f"{endpoint}: {response.status_code}")
            if response.status_code == 200:
                data = response.json()
                if 'success' in data and data['success']:
                    print(f"  Success: {data['success']}, Data items: {len(data['data'])}")
                else:
                    print(f"  Keys: {list(data.keys())}")
            else:
                print(f"  Error: {response.text}")
        except Exception as e:
            print(f"{endpoint}: ERROR - {e}")

if __name__ == '__main__':
    test_api_endpoints()
