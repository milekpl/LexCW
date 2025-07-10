#!/usr/bin/env python3
"""
Test script to debug web endpoint submissions
"""
import requests
import json

import pytest

@pytest.mark.integration
def test_json_submission():
    """Test JSON submission to web endpoint"""
    url = "http://localhost:5000/entries/add"
    
    # Minimal test data
    data = {
        "lexical_unit": {"en": "test"},
        "senses": [{
            "definition": {"en": "a test word"}
        }]
    }
    
    print("Testing JSON submission...")
    print(f"URL: {url}")
    print(f"Data: {json.dumps(data, indent=2)}")
    
    try:
        response = requests.post(
            url, 
            json=data,
            headers={'Content-Type': 'application/json'}
        )
        
        print(f"\nResponse Status: {response.status_code}")
        print(f"Response Headers: {dict(response.headers)}")
        
        try:
            response_data = response.json()
            print(f"Response JSON: {json.dumps(response_data, indent=2)}")
        except:
            print(f"Response Text: {response.text}")
            
    except Exception as e:
        print(f"Error: {e}")

@pytest.mark.integration
def test_form_submission():
    """Test form data submission to web endpoint"""
    url = "http://localhost:5000/entries/add"
    
    # Minimal test data as form data
    data = {
        "lexical_unit[en]": "test",
        "senses[0][definition][en]": "a test word"
    }
    
    print("\n" + "="*50)
    print("Testing form submission...")
    print(f"URL: {url}")
    print(f"Data: {data}")
    
    try:
        response = requests.post(url, data=data)
        
        print(f"\nResponse Status: {response.status_code}")
        print(f"Response Headers: {dict(response.headers)}")
        
        try:
            response_data = response.json()
            print(f"Response JSON: {json.dumps(response_data, indent=2)}")
        except:
            print(f"Response Text: {response.text[:500]}...")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_json_submission()
    test_form_submission()
