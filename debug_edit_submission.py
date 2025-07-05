#!/usr/bin/env python3
"""
Debug script to test web form submission exactly like the frontend
"""
import requests
import json

def test_edit_submission():
    """Test editing the specific AIDS test entry"""
    url = "http://localhost:5000/entries/AIDS%20test_a774b9c4-c013-4f54-9017-cf818791080c/edit"
    
    # Get the entry first to see its current state
    print("=== GETTING CURRENT ENTRY ===")
    get_response = requests.get(url)
    print(f"GET Status: {get_response.status_code}")
    
    # Now test a minimal update (just try to save without changes)
    print("\n=== TESTING EDIT SUBMISSION ===")
    
    # Minimal data that should preserve the existing entry
    data = {
        "lexical_unit": {"en": "AIDS test"},
        "senses": [{
            "id": "aaaee4d6-8239-43e3-819c-c246932b0ae0",
            "definition": {"pl": "test na obecność wirusa HIV"}
        }]
    }
    
    print(f"Submitting data: {json.dumps(data, indent=2)}")
    
    try:
        response = requests.post(
            url, 
            json=data,
            headers={'Content-Type': 'application/json'}
        )
        
        print(f"\nResponse Status: {response.status_code}")
        
        try:
            response_data = response.json()
            print(f"Response JSON: {json.dumps(response_data, indent=2)}")
        except:
            print(f"Response Text: {response.text}")
            
    except Exception as e:
        print(f"Error: {e}")

def test_edit_with_form_data():
    """Test with form data format"""
    url = "http://localhost:5000/entries/AIDS%20test_a774b9c4-c013-4f54-9017-cf818791080c/edit"
    
    print("\n=== TESTING FORM DATA SUBMISSION ===")
    
    # Form data format
    data = {
        "lexical_unit[en]": "AIDS test",
        "senses[0][id]": "aaaee4d6-8239-43e3-819c-c246932b0ae0",
        "senses[0][definition][pl]": "test na obecność wirusa HIV"
    }
    
    print(f"Submitting form data: {data}")
    
    try:
        response = requests.post(url, data=data)
        
        print(f"\nResponse Status: {response.status_code}")
        
        try:
            response_data = response.json()
            print(f"Response JSON: {json.dumps(response_data, indent=2)}")
        except:
            print(f"Response Text: {response.text[:500]}...")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_edit_submission()
    test_edit_with_form_data()
