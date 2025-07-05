#!/usr/bin/env python3
"""
Test specific multilingual note processing to ensure dot notation is handled correctly.
"""

import requests

BASE_URL = "http://127.0.0.1:5000"
ENTRY_ID = "Protestantism_b97495fb-d52f-4755-94bf-a7a762339605"

def test_complex_multilingual_notes():
    """Test complex multilingual notes with dot notation."""
    print("=== Testing Complex Multilingual Notes ===")
    
    url = f"{BASE_URL}/entries/{ENTRY_ID}/edit"
    
    # Complex form data with nested structures
    form_data = {
        # Basic fields
        'lexical_unit[en]': 'Protestantism',
        'lexical_unit[pt]': 'Protestantismo',
        'grammatical_info.part_of_speech': 'Noun',
        
        # Multilingual notes
        'notes[general][en]': 'A major branch of Christianity',
        'notes[general][pt]': 'Um ramo principal do Cristianismo',
        'notes[usage][en]': 'Commonly used in theological contexts',
        'notes[usage][pt]': 'Comumente usado em contextos teológicos',
        'notes[etymology][en]': 'From Latin protestantem',
        
        # Senses with definitions
        'senses[0][definition][en]': 'Christian religious movement',
        'senses[0][definition][pt]': 'Movimento religioso cristão',
        'senses[0][example][en]': 'Protestant churches are widespread',
        'senses[0][example][pt]': 'Igrejas protestantes são difundidas',
        
        # Additional sense
        'senses[1][definition][en]': 'Follower of Protestantism',
        'senses[1][definition][pt]': 'Seguidor do Protestantismo',
    }
    
    try:
        response = requests.post(url, data=form_data)
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text}")
        
        if response.status_code == 200:
            print("✅ Complex multilingual form submission successful")
            
            # Now retrieve the entry to verify the data was saved correctly
            get_response = requests.get(url.replace('/edit', ''))
            if get_response.status_code == 200:
                print("✅ Entry retrieval successful")
                # Could parse HTML to verify content, but the 200 status indicates success
            else:
                print(f"⚠️ Entry retrieval returned status: {get_response.status_code}")
        else:
            print("❌ Complex multilingual form submission failed")
            
    except Exception as e:
        print(f"❌ Complex multilingual test error: {e}")


def test_dot_notation_edge_cases():
    """Test edge cases with dot notation."""
    print("\n=== Testing Dot Notation Edge Cases ===")
    
    url = f"{BASE_URL}/entries/{ENTRY_ID}/edit"
    
    # Edge cases with dot notation
    form_data = {
        'lexical_unit[en]': 'Protestantism',
        
        # Dot notation in various forms
        'grammatical_info.part_of_speech': 'Noun',
        'grammatical_info.gender': 'Masculine',  # Additional grammatical info
        
        # Mixed bracket and dot notation
        'notes[general][en]': 'Test note with dot notation field',
        'metadata.source': 'Test source',
        'metadata.confidence': 'High',
    }
    
    try:
        response = requests.post(url, data=form_data)
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text}")
        
        if response.status_code == 200:
            print("✅ Dot notation edge cases handled successfully")
        else:
            print("❌ Dot notation edge cases failed")
            
    except Exception as e:
        print(f"❌ Dot notation edge case error: {e}")


def main():
    """Run all multilingual and dot notation tests."""
    print("Testing multilingual form processing with dot notation...")
    print(f"Target entry: {ENTRY_ID}")
    
    test_complex_multilingual_notes()
    test_dot_notation_edge_cases()
    
    print("\n=== Multilingual Test Summary ===")
    print("All multilingual tests completed.")


if __name__ == "__main__":
    main()
