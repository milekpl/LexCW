#!/usr/bin/env python3
"""
Test specific frontend data structure that might be causing the validation error
"""
import requests
import json

def test_frontend_like_data():
    """Test with data structure that mimics what frontend sends"""
    url = "http://localhost:5000/entries/AIDS%20test_a774b9c4-c013-4f54-9017-cf818791080c/edit"
    
    # More complete data structure that includes all fields frontend might send
    data = {
        "id": "AIDS test_a774b9c4-c013-4f54-9017-cf818791080c",
        "lexical_unit": {"en": "AIDS test"},
        "pronunciations": [{"value": "eɪdz test", "lang": "seh-fonipa"}],
        "grammatical_info": "",
        "notes": {},
        "senses": [{
            "id": "aaaee4d6-8239-43e3-819c-c246932b0ae0",
            "definition": {"pl": "test na obecność wirusa HIV"},
            "gloss": {},
            "examples": [],
            "notes": {}
        }]
    }
    
    print("=== TESTING COMPLETE FRONTEND-LIKE DATA ===")
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

def test_minimal_sense_data():
    """Test with minimal sense data that might trigger validation error"""
    url = "http://localhost:5000/entries/AIDS%20test_a774b9c4-c013-4f54-9017-cf818791080c/edit"
    
    # Try with empty or minimal sense
    data = {
        "id": "AIDS test_a774b9c4-c013-4f54-9017-cf818791080c",
        "lexical_unit": {"en": "AIDS test"},
        "senses": [{
            "id": "aaaee4d6-8239-43e3-819c-c246932b0ae0",
            # Missing definition - this might trigger the error
        }]
    }
    
    print("\n=== TESTING MINIMAL SENSE DATA (SHOULD FAIL) ===")
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

def test_empty_definition():
    """Test with empty definition"""
    url = "http://localhost:5000/entries/AIDS%20test_a774b9c4-c013-4f54-9017-cf818791080c/edit"
    
    # Try with empty definition
    data = {
        "id": "AIDS test_a774b9c4-c013-4f54-9017-cf818791080c",
        "lexical_unit": {"en": "AIDS test"},
        "senses": [{
            "id": "aaaee4d6-8239-43e3-819c-c246932b0ae0",
            "definition": {},  # Empty definition object
            "gloss": ""
        }]
    }
    
    print("\n=== TESTING EMPTY DEFINITION (SHOULD FAIL) ===")
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

if __name__ == "__main__":
    test_frontend_like_data()
    test_minimal_sense_data()
    test_empty_definition()
