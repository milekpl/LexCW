#!/usr/bin/env python3
"""
Test API endpoint to verify entry retrieval works.
"""

import requests

def test_api_entry_retrieval():
    """Test API entry retrieval."""
    
    try:
        # Test API endpoint
        response = requests.get("http://localhost:5000/api/entries/ui-test-entry", timeout=30)
        
        if response.status_code == 200:
            print("API entry retrieval successful!")
            data = response.json()
            print("Entry ID:", data.get('id'))
            print("Lexical unit:", data.get('lexical_unit'))
            print("Relations count:", len(data.get('relations', [])))
            print("Relations:", data.get('relations', []))
            return True
        else:
            print(f"API request failed. Status: {response.status_code}")
            print("Response:", response.text)
            return False
            
    except Exception as e:
        print(f"Error retrieving entry: {e}")
        return False

if __name__ == "__main__":
    success = test_api_entry_retrieval()
    if success:
        print("\nAPI endpoint working correctly!")
    else:
        print("API endpoint test failed")
