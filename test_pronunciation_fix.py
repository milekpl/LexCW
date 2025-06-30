#!/usr/bin/env python3
"""
Test script to verify pronunciation handling, especially 'seh-fonipa' language codes.
"""

from app.models.entry import Entry
from app.models.sense import Sense
import json

def test_pronunciation_handling():
    """Test that pronunciations with non-standard language codes work correctly."""
    print("Testing pronunciation handling...")
    
    # Create an entry with various pronunciations including 'seh-fonipa'
    entry = Entry(
        id_="test_pronunciation",
        lexical_unit={"en": "test", "seh": "test"},
        pronunciations={
            "seh-fonipa": "/tɛst/",
            "en-ipa": "/tɛst/",
            "seh": "test"
        },
        senses=[
            Sense(
                id_="test_sense",
                gloss={"en": "a test", "seh": "teste"}
            )
        ]
    )
    
    print(f"Entry ID: {entry.id}")
    print(f"Lexical Unit: {entry.lexical_unit}")
    print(f"Pronunciations: {entry.pronunciations}")
    
    # Test to_dict method
    entry_dict = entry.to_dict()
    print(f"Entry as dict: {json.dumps(entry_dict, indent=2)}")
    
    # Test JSON serialization
    entry_json = entry.to_json()
    print(f"Entry as JSON: {entry_json}")
    
    # Verify pronunciation data integrity
    assert 'seh-fonipa' in entry.pronunciations
    assert entry.pronunciations['seh-fonipa'] == "/tɛst/"
    assert 'en-ipa' in entry.pronunciations
    assert entry.pronunciations['en-ipa'] == "/tɛst/"
    
    # Verify in serialized form
    assert 'pronunciations' in entry_dict
    assert 'seh-fonipa' in entry_dict['pronunciations']
    assert entry_dict['pronunciations']['seh-fonipa'] == "/tɛst/"
    
    print("✓ All pronunciation tests passed!")
    return True

if __name__ == "__main__":
    test_pronunciation_handling()
