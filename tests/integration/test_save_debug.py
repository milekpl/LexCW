#!/usr/bin/env python3
"""
Test script to debug entry save issues.

This script tests:
1. Creating an entry without POS (should work)
2. Creating a phrase entry (should not require POS)
3. Examining save errors
"""

import requests
import json

import pytest

@pytest.mark.integration
def test_entry_save():
    """Test entry saving to identify the error."""
    
    base_url = "http://127.0.0.1:5000"
    
    # Test 1: Try to create a simple entry without POS
    print("🧪 Test 1: Creating entry without POS")
    
    test_data = {
        'lexical_unit': 'test-word',
        'citation_form': '',
        'grammatical_info.part_of_speech': '',  # Empty POS
        'semantic_domain': '',
        'senses[0].definition': 'A test definition',
        'senses[0].gloss': 'test',
        'senses[0].grammatical_info': '',
        'senses[0].note': ''
    }
    
    try:
        response = requests.post(f"{base_url}/entries/add", data=test_data)
        print(f"  📊 Response status: {response.status_code}")
        print(f"  📊 Response headers: {dict(response.headers)}")
        
        if response.status_code == 200:
            print("  ✅ Entry saved successfully")
        else:
            print(f"  ❌ Save failed with status {response.status_code}")
            print(f"  📄 Response text: {response.text[:500]}...")
            
    except Exception as e:
        print(f"  ❌ Request failed: {e}")
    
    # Test 2: Try to create a phrase entry (should not require POS)
    print("\n🧪 Test 2: Creating phrase entry")
    
    phrase_data = {
        'lexical_unit': 'test phrase with spaces',  # This should be classified as phrase
        'citation_form': '',
        'grammatical_info.part_of_speech': '',  # Empty POS for phrase
        'semantic_domain': '',
        'senses[0].definition': 'A test phrase definition',
        'senses[0].gloss': 'test phrase',
        'senses[0].grammatical_info': '',
        'senses[0].note': ''
    }
    
    try:
        response = requests.post(f"{base_url}/entries/add", data=phrase_data)
        print(f"  📊 Response status: {response.status_code}")
        
        if response.status_code == 200:
            print("  ✅ Phrase entry saved successfully")
        else:
            print(f"  ❌ Phrase save failed with status {response.status_code}")
            print(f"  📄 Response text: {response.text[:500]}...")
            
    except Exception as e:
        print(f"  ❌ Request failed: {e}")
    
    # Test 3: Check form validation in browser
    print("\n🧪 Test 3: Checking form validation")
    
    try:
        response = requests.get(f"{base_url}/entries/add")
        if response.status_code == 200:
            form_html = response.text
            
            # Check for required attributes
            if 'required' in form_html:
                print("  📊 Found 'required' attributes in form")
                # Count required fields
                required_count = form_html.count('required')
                print(f"  📊 Number of required fields: {required_count}")
            else:
                print("  📊 No 'required' attributes found in form HTML")
                
            # Check for JavaScript validation
            if 'entryPartOfSpeechSelect.required = true' in form_html:
                print("  ⚠️  JavaScript sets POS as required")
            
        else:
            print(f"  ❌ Could not load form: {response.status_code}")
            
    except Exception as e:
        print(f"  ❌ Error checking form: {e}")

if __name__ == "__main__":
    test_entry_save()
