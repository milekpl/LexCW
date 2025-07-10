#!/usr/bin/env python3
"""
Test the exact scenario: form sends single definition field vs multilingual existing data
"""
import requests
import json

import pytest

@pytest.mark.integration
def test_single_definition_field():
    """Test what happens when form sends a single definition field"""
    url = "http://localhost:5000/entries/AIDS%20test_a774b9c4-c013-4f54-9017-cf818791080c/edit"
    
    # This mimics what the frontend form actually sends:
    # <textarea name="senses[0].definition">test na obecność wirusa HIV</textarea>
    data = {
        "lexical_unit": {"en": "AIDS test"},
        "senses": [{
            "id": "aaaee4d6-8239-43e3-819c-c246932b0ae0",
            "definition": "test na obecność wirusa HIV"  # Single string, not multilingual object
        }]
    }
    
    print("=== TESTING SINGLE DEFINITION STRING ===")
    print(f"Sending data: {json.dumps(data, indent=2)}")
    
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

@pytest.mark.integration
def test_form_data_single_definition():
    """Test using actual form data format"""
    url = "http://localhost:5000/entries/AIDS%20test_a774b9c4-c013-4f54-9017-cf818791080c/edit"
    
    # This is exactly what the frontend form sends
    data = {
        "lexical_unit[en]": "AIDS test",
        "senses[0][id]": "aaaee4d6-8239-43e3-819c-c246932b0ae0",
        "senses[0].definition": "test na obecność wirusa HIV"  # Note the dot notation
    }
    
    print("\n=== TESTING FORM DATA WITH DOT NOTATION ===")
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

@pytest.mark.integration
def test_empty_single_definition():
    """Test empty single definition field"""
    url = "http://localhost:5000/entries/AIDS%20test_a774b9c4-c013-4f54-9017-cf818791080c/edit"
    
    # Empty definition
    data = {
        "lexical_unit[en]": "AIDS test",
        "senses[0][id]": "aaaee4d6-8239-43e3-819c-c246932b0ae0",
        "senses[0].definition": ""  # Empty definition - this might trigger the error!
    }
    
    print("\n=== TESTING EMPTY SINGLE DEFINITION ===")
    print(f"Sending form data: {data}")
    
    try:
        response = requests.post(url, data=data)
        
        print(f"\nResponse Status: {response.status_code}")
        
        try:
            response_data = response.json()
            print(f"Response: {json.dumps(response_data, indent=2)}")
        except:
            print(f"Response Text: {response.text}")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_single_definition_field()
    test_form_data_single_definition()
    test_empty_single_definition()
