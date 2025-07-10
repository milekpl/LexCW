#!/usr/bin/env python3
"""
Test complex form submission that might trigger the serialization error.
"""

import requests

import pytest

@pytest.mark.integration
def test_complex_form_submission():
    """Test complex form data that might cause the serialization error."""
    print("=== Testing Complex Form Submission ===")
    
    url = "http://127.0.0.1:5000/entries/Protestantism_b97495fb-d52f-4755-94bf-a7a762339605/edit"
    
    # Complex form data similar to what a real browser might send
    form_data = {
        'lexical_unit[en]': 'Protestantism',
        'grammatical_info.part_of_speech': 'Noun',
        'notes[general][en]': 'A form of Christianity',
        
        # Complex senses with multiple languages 
        'senses[0][definition][en]': 'Christian religious movement',
        'senses[0][gloss][en]': 'Protestant faith',
        'senses[0][grammatical_info]': 'noun.common',
        
        # Second sense
        'senses[1][definition][en]': 'Follower of Protestantism',
        'senses[1][gloss][en]': 'Protestant person',
        
        # Examples
        'senses[0][examples][0][text]': 'Protestant churches are widespread',
        'senses[0][examples][0][source]': 'Religious text',
    }
    
    print(f"Sending complex form data to: {url}")
    print("Form data:")
    for key, value in form_data.items():
        print(f"  {key}: {value}")
    
    try:
        response = requests.post(url, data=form_data)
        print(f"\nResponse Status: {response.status_code}")
        print(f"Response: {response.text}")
        
        if response.status_code == 200:
            print("✅ Complex form submission successful")
        else:
            print("❌ Complex form submission failed")
            
    except Exception as e:
        print(f"❌ Error during test: {e}")

@pytest.mark.integration
def test_problematic_multilingual_data():
    """Test data that might cause serialization issues."""
    print("\n=== Testing Potentially Problematic Data ===")
    
    url = "http://127.0.0.1:5000/entries/Protestantism_b97495fb-d52f-4755-94bf-a7a762339605/edit"
    
    # Data that might cause dict serialization issues
    form_data = {
        'lexical_unit[en]': 'Protestantism',
        'grammatical_info.part_of_speech': 'Noun',
        
        # Empty or problematic senses
        'senses[0][definition][en]': '',  # Empty definition
        'senses[0][definition][pt]': 'Portuguese definition',  # Portuguese not allowed according to user
        'senses[1][definition][en]': 'Valid definition',
        
        # Notes with potential issues
        'notes[general][en]': 'English note',
        'notes[general][pt]': 'Portuguese note',  # Portuguese not allowed
    }
    
    print(f"Sending potentially problematic data to: {url}")
    print("Form data:")
    for key, value in form_data.items():
        print(f"  {key}: {value}")
    
    try:
        response = requests.post(url, data=form_data)
        print(f"\nResponse Status: {response.status_code}")
        print(f"Response: {response.text}")
        
        if response.status_code == 200:
            print("✅ Problematic data handled successfully")
        else:
            print("❌ Problematic data caused issues")
            
    except Exception as e:
        print(f"❌ Error during test: {e}")

def main():
    """Run complex form tests."""
    print("TESTING COMPLEX FORM SUBMISSIONS")
    print("=" * 50)
    
    test_complex_form_submission()
    test_problematic_multilingual_data()

if __name__ == "__main__":
    main()
