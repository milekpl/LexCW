"""Test to manually check POS inheritance behavior in browser."""

import requests
import time

def test_entry_update():
    """Test entry update with specific data."""
    
    # Get the form page first to ensure server is ready
    try:
        response = requests.get("http://127.0.0.1:5000/entries/new")
        if response.status_code == 200:
            print("✓ Entry form accessible")
        else:
            print(f"✗ Entry form error: {response.status_code}")
            return
            
    except Exception as e:
        print(f"✗ Failed to access entry form: {e}")
        return
        
    # Test entry creation with multiple senses
    entry_data = {
        'headword': 'test_word',
        'senses': [
            {
                'definition': {'en': 'First meaning'},
                'grammatical_info': 'Noun'
            },
            {
                'definition': {'en': 'Second meaning'},
                'grammatical_info': 'Noun'
            }
        ]
    }
    
    try:
        response = requests.post("http://127.0.0.1:5000/entries/new", json=entry_data)
        print(f"Entry creation response: {response.status_code}")
        if response.status_code != 200:
            print(f"Response content: {response.text}")
    except Exception as e:
        print(f"✗ Entry creation failed: {e}")

if __name__ == "__main__":
    test_entry_update()
