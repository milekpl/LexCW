#!/usr/bin/env python3
"""
Test script to debug the exact data being sent by the frontend
"""
import requests
import json

def test_with_more_complete_data():
    """Test with more complete data that matches what the frontend would send"""
    url = "http://localhost:5000/entries/add"
    
    # Test data that matches what the frontend JavaScript creates
    data = {
        "lexical_unit": {
            "en": "test"
        },
        "senses": [
            {
                "definition": {
                    "en": "a test word"
                },
                "examples": []
            }
        ],
        "notes": {},
        "pronunciation": [],
        "grammatical_info": ""
    }
    
    print("Testing with complete frontend-like data...")
    print(f"Data: {json.dumps(data, indent=2)}")
    
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

def test_minimal_json():
    """Test absolute minimal JSON"""
    url = "http://localhost:5000/entries/add"
    
    # Absolute minimal data
    data = {
        "lexical_unit": {"en": "minimal"},
    }
    
    print("\n" + "="*50)
    print("Testing with minimal JSON data...")
    print(f"Data: {json.dumps(data, indent=2)}")
    
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

def test_debug_processing():
    """Test to debug what happens during processing"""
    # Let's first check what merge_form_data_with_entry_data does with our data
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    
    from app.utils.multilingual_form_processor import merge_form_data_with_entry_data
    
    data = {
        "lexical_unit": {"en": "test"},
        "senses": [{"definition": {"en": "a test word"}}]
    }
    
    print("\n" + "="*50)
    print("Testing local processing...")
    print(f"Input data: {json.dumps(data, indent=2)}")
    
    try:
        empty_entry_data = {}
        merged_data = merge_form_data_with_entry_data(data, empty_entry_data)
        print(f"Merged data: {json.dumps(merged_data, indent=2)}")
        
        # Test Entry creation
        from app.models.entry import Entry
        entry = Entry.from_dict(merged_data)
        print(f"Entry created successfully: {entry}")
        print(f"Entry lexical_unit: {entry.lexical_unit}")
        
    except Exception as e:
        print(f"Local processing error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_with_more_complete_data()
    test_minimal_json()
    test_debug_processing()
