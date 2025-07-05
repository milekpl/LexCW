#!/usr/bin/env python3
"""
Test what happens when we send incomplete sense data
"""
import requests
import json

def test_incomplete_sense_submission():
    """Test sending a sense without definition to see if it gets preserved"""
    url = "http://localhost:5000/entries/AIDS%20test_a774b9c4-c013-4f54-9017-cf818791080c/edit"
    
    # Send sense with ID but no definition - should preserve existing definition
    data = {
        "lexical_unit": {"en": "AIDS test"},
        "senses": [{
            "id": "aaaee4d6-8239-43e3-819c-c246932b0ae0",
            # NO definition field - should be preserved from existing
            "examples": []  # Include some field to make sense non-empty
        }]
    }
    
    print("=== TESTING INCOMPLETE SENSE SUBMISSION ===")
    print(f"Sending data WITHOUT definition: {json.dumps(data, indent=2)}")
    
    try:
        response = requests.post(
            url, 
            json=data,
            headers={'Content-Type': 'application/json'}
        )
        
        print(f"\nResponse Status: {response.status_code}")
        
        try:
            response_data = response.json()
            print(f"Response: {json.dumps(response_data, indent=2)}")
        except:
            print(f"Response Text: {response.text}")
            
    except Exception as e:
        print(f"Error: {e}")

def test_explicit_empty_definition():
    """Test sending explicit empty definition"""
    url = "http://localhost:5000/entries/AIDS%20test_a774b9c4-c013-4f54-9017-cf818791080c/edit"
    
    # Send sense with explicitly empty definition - might trigger error
    data = {
        "lexical_unit": {"en": "AIDS test"},
        "senses": [{
            "id": "aaaee4d6-8239-43e3-819c-c246932b0ae0",
            "definition": "",  # Explicitly empty
            "examples": []
        }]
    }
    
    print("\n=== TESTING EXPLICIT EMPTY DEFINITION ===")
    print(f"Sending data with empty definition: {json.dumps(data, indent=2)}")
    
    try:
        response = requests.post(
            url, 
            json=data,
            headers={'Content-Type': 'application/json'}
        )
        
        print(f"\nResponse Status: {response.status_code}")
        
        try:
            response_data = response.json()
            print(f"Response: {json.dumps(response_data, indent=2)}")
        except:
            print(f"Response Text: {response.text}")
            
    except Exception as e:
        print(f"Error: {e}")

def test_form_data_style():
    """Test form data submission style that might match frontend"""
    url = "http://localhost:5000/entries/AIDS%20test_a774b9c4-c013-4f54-9017-cf818791080c/edit"
    
    # Form data that might not include definition field
    data = {
        "lexical_unit[en]": "AIDS test",
        "senses[0][id]": "aaaee4d6-8239-43e3-819c-c246932b0ae0",
        # NO definition field at all
        "senses[0][examples]": ""
    }
    
    print("\n=== TESTING FORM DATA WITHOUT DEFINITION ===")
    print(f"Sending form data: {data}")
    
    try:
        response = requests.post(url, data=data)
        
        print(f"\nResponse Status: {response.status_code}")
        
        try:
            response_data = response.json()
            print(f"Response: {json.dumps(response_data, indent=2)}")
        except:
            print(f"Response Text: {response.text[:500]}...")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_incomplete_sense_submission()
    test_explicit_empty_definition()
    test_form_data_style()
