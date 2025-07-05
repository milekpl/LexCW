#!/usr/bin/env python3
"""
Manual test to verify that the web application properly preserves data during entry editing.

This test simulates the exact scenario described by the user:
1. Create an entry with a definition
2. Edit it without making changes (or make minimal changes)
3. Verify that the definition is preserved
"""

import requests
import json
import time


def test_web_application_data_preservation():
    """Test the actual web application data preservation."""
    
    base_url = "http://127.0.0.1:5000"
    
    print("🔍 Testing web application data preservation...")
    
    # 1. First, create a test entry via the API
    print("\n1. Creating test entry...")
    create_data = {
        "id": "manual_test_entry",
        "lexical_unit": {"en": "testword"},
        "senses": [
            {
                "id": "sense1",
                "definition": {"en": "Original definition that should NOT be lost"},
                "grammatical_info": "noun"
            }
        ]
    }
    
    try:
        # Create via POST to /entries/add endpoint
        create_response = requests.post(
            f"{base_url}/entries/add",
            json=create_data,
            headers={"Content-Type": "application/json"}
        )
        
        if create_response.status_code == 200:
            result = create_response.json()
            entry_id = result.get('id', 'manual_test_entry')
            print(f"✅ Entry created successfully with ID: {entry_id}")
        else:
            print(f"❌ Failed to create entry: {create_response.status_code}")
            print(f"Response: {create_response.text}")
            return False
            
        # 2. Get the entry to verify it was created correctly
        print(f"\n2. Verifying entry creation...")
        get_response = requests.get(f"{base_url}/api/entries/{entry_id}")
        
        if get_response.status_code == 200:
            original_entry = get_response.json()
            original_definition = original_entry.get('senses', [{}])[0].get('definition')
            print(f"✅ Original definition: {original_definition}")
        else:
            print(f"❌ Failed to get entry: {get_response.status_code}")
            return False
            
        # 3. Simulate editing the entry with minimal changes (just like user would do)
        print(f"\n3. Simulating entry edit with minimal form data...")
        
        # This simulates what the JavaScript form would send when user saves with minimal changes
        edit_data = {
            "id": entry_id,
            "lexical_unit": {"en": "testword"},  # Same value
            "senses": [
                {
                    "id": "sense1",
                    # NOTE: Definition and grammatical_info might be missing if user didn't edit those fields
                    # This is the critical test case
                }
            ]
        }
        
        edit_response = requests.post(
            f"{base_url}/entries/{entry_id}/edit",
            json=edit_data,
            headers={"Content-Type": "application/json"}
        )
        
        if edit_response.status_code == 200:
            print("✅ Entry edit request successful")
        else:
            print(f"❌ Failed to edit entry: {edit_response.status_code}")
            print(f"Response: {edit_response.text}")
            return False
            
        # 4. Get the entry again to verify data was preserved
        print(f"\n4. Verifying data preservation after edit...")
        
        time.sleep(0.5)  # Small delay to ensure persistence
        
        get_response2 = requests.get(f"{base_url}/api/entries/{entry_id}")
        
        if get_response2.status_code == 200:
            updated_entry = get_response2.json()
            updated_definition = updated_entry.get('senses', [{}])[0].get('definition')
            updated_grammatical_info = updated_entry.get('senses', [{}])[0].get('grammatical_info')
            
            print(f"📊 Results:")
            print(f"   Original definition: {original_definition}")
            print(f"   Updated definition:  {updated_definition}")
            print(f"   Updated grammatical_info: {updated_grammatical_info}")
            
            # Critical check: data should be preserved
            if updated_definition == original_definition:
                print("✅ SUCCESS: Definition was preserved!")
                success = True
            else:
                print("❌ FAILURE: Definition was lost!")
                success = False
                
            if updated_grammatical_info == "noun":
                print("✅ SUCCESS: Grammatical info was preserved!")
            else:
                print("❌ FAILURE: Grammatical info was lost!")
                success = False
                
            return success
        else:
            print(f"❌ Failed to get updated entry: {get_response2.status_code}")
            return False
            
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to Flask application. Make sure it's running on http://127.0.0.1:5000")
        print("   Run: python run.py")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False


if __name__ == "__main__":
    print("Manual Web Application Data Preservation Test")
    print("=" * 50)
    
    success = test_web_application_data_preservation()
    
    print("\n" + "=" * 50)
    if success:
        print("🎉 TEST PASSED: Web application preserves data correctly!")
    else:
        print("💥 TEST FAILED: Web application has data loss issues!")
    
    print("\nTo run this test:")
    print("1. Start the Flask app: python run.py")
    print("2. Run this test: python manual_test_web_data_preservation.py")
