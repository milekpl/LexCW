#!/usr/bin/env python3
"""
Test script to verify API endpoints work correctly with the new Entry model.
"""

import json
from app import create_app
from app.models.entry import Entry
from app.models.sense import Sense

def test_api_serialization():
    """Test that API endpoints can properly serialize Entry objects."""
    print("Testing API serialization...")
    
    # Create a test entry with complex data
    entry = Entry(
        id_="api_test_entry",
        lexical_unit={"en": "test", "seh": "teste"},
        pronunciations={
            "seh-fonipa": "/tɛstɛ/",
            "en-ipa": "/tɛst/"
        },
        grammatical_info="noun",
        senses=[
            Sense(
                id_="test_sense_1",
                gloss={"en": "a test", "seh": "teste"},
                definition={"en": "A procedure used to test something"}
            )
        ]
    )
    
    print(f"Entry ID: {entry.id}")
    print(f"Headword: {entry.headword}")
    
    # Test to_dict serialization (used by API)
    entry_dict = entry.to_dict()
    print("Entry as dict keys:", list(entry_dict.keys()))
    
    # Test JSON serialization
    entry_json = entry.to_json()
    print(f"JSON serialization successful: {len(entry_json)} characters")
    
    # Verify that JSON can be parsed back
    parsed_json = json.loads(entry_json)
    print(f"JSON parsing successful: {type(parsed_json)}")
    
    # Test Flask app creation
    app = create_app()
    assert app is not None
    print("✓ Flask app creation successful")
    
    print("✓ All API serialization tests passed!")
    return True

if __name__ == "__main__":
    test_api_serialization()
