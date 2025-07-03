"""
Test script to add an entry with EXAMPLE_TRANSLATION and search for it.
"""

import json
import requests

# Create an entry with EXAMPLE_TRANSLATION in the notes
entry_data = {
    'id': 'test-example-translation-entry',
    'lexical_unit': {'en': 'example', 'pt': 'exemplo'},
    'notes': {
        'general': {
            'en': 'This note contains EXAMPLE_TRANSLATION for testing',
            'pt': 'Esta nota contém EXAMPLE_TRANSLATION para testes'
        },
        'usage': {
            'en': 'Test entry with EXAMPLE_TRANSLATION in usage note'
        }
    }
}

def test_example_translation_search():
    """Test creating an entry and searching for EXAMPLE_TRANSLATION."""
    
    print("Testing EXAMPLE_TRANSLATION search...")
    
    # First, try to add the entry (this might fail if we're in test mode)
    try:
        response = requests.post('http://localhost:5000/entries/add', 
                               json=entry_data,
                               headers={'Content-Type': 'application/json'})
        print(f"Add entry response: {response.status_code}")
        if response.status_code == 200:
            result = response.json()
            print(f"Entry created: {result}")
    except Exception as e:
        print(f"Could not add entry (expected in test mode): {e}")
    
    # Now search for EXAMPLE_TRANSLATION
    search_params = {
        'q': 'EXAMPLE_TRANSLATION',
        'fields': 'notes,lexical_unit',
        'limit': 10
    }
    
    try:
        response = requests.get('http://localhost:5000/api/search/', params=search_params)
        print(f"Search response status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"Search results for 'EXAMPLE_TRANSLATION': {json.dumps(data, indent=2)}")
            
            if data['total'] > 0:
                print("✅ Found entries with EXAMPLE_TRANSLATION!")
                for entry in data['entries']:
                    if 'notes' in entry:
                        print(f"Entry notes: {entry['notes']}")
            else:
                print("❌ No entries found with EXAMPLE_TRANSLATION")
        else:
            print(f"Search failed: {response.text}")
            
    except Exception as e:
        print(f"Search request failed: {e}")

if __name__ == "__main__":
    test_example_translation_search()
