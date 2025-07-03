#!/usr/bin/env python3
"""
Write a test for PronunciationFormsManager debugging.
"""

def write_test():
    """Write a test unit for debugging pronunciation forms."""
    test_content = """
import pytest
from flask import current_app
from app.services.dictionary_service import DictionaryService
from app.models.entry import Entry

def test_pronunciation_display_debug(client):
    '''Test pronunciation display debugging.'''
    # Get entry with pronunciations 
    dict_service = current_app.injector.get(DictionaryService)
    entry = dict_service.get_entry('Protestant1_8c895a90-6c91-4257-8ada-528e18d2ba69')
    
    # Test that pronunciations exist
    assert entry.pronunciations is not None
    assert len(entry.pronunciations) > 0
    
    # Test template rendering
    response = client.get(f'/entries/{entry.id}/edit')
    assert response.status_code == 200
    
    # Check that pronunciation data is in the response
    response_text = response.get_data(as_text=True)
    assert 'pronunciation-container' in response_text
    assert 'PronunciationFormsManager' in response_text
    
    # Check that the pronunciation value is properly encoded
    for lang, value in entry.pronunciations.items():
        # The value should be JSON-encoded in the script
        import json
        encoded_value = json.dumps(value)
        assert encoded_value in response_text
        print(f"Found encoded pronunciation: {encoded_value}")
"""
    
    with open('d:\\Dokumenty\\slownik-wielki\\flask-app\\tests\\test_pronunciation_debug.py', 'w', encoding='utf-8') as f:
        f.write(test_content)
    
    print("Created test file: tests/test_pronunciation_debug.py")

if __name__ == '__main__':
    write_test()
