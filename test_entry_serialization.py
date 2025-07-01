#!/usr/bin/env python3
"""
Test script to verify entry serialization works properly.
"""

import json
from app.models.entry import Entry, Relation, Etymology, Form, Gloss

def test_entry_serialization():
    """Test that Entry objects with relations can be serialized to JSON."""
    
    # Create an entry with relations
    entry = Entry(
        id_="test-entry",
        lexical_unit={"en": "test word"},
        relations=[
            {"type": "synonym", "ref": "synonym-entry"},
            {"type": "antonym", "ref": "antonym-entry"}
        ],
        etymologies=[
            {
                "type": "borrowing",
                "source": "Latin",
                "form": {"lang": "la", "text": "testum"},
                "gloss": {"lang": "en", "text": "test"}
            }
        ]
    )
    
    # Test to_dict conversion
    entry_dict = entry.to_dict()
    print("Entry dict keys:", list(entry_dict.keys()))
    print("Relations type:", type(entry_dict.get('relations', [])))
    print("Relations content:", entry_dict.get('relations', []))
    
    # Test JSON serialization
    try:
        json_str = json.dumps(entry_dict)
        print("JSON serialization successful!")
        print("JSON length:", len(json_str))
        
        # Test round-trip
        parsed = json.loads(json_str)
        print("JSON parsing successful!")
        
        return True
        
    except Exception as e:
        print(f"JSON serialization failed: {e}")
        return False

if __name__ == "__main__":
    success = test_entry_serialization()
    if success:
        print("Entry serialization test PASSED")
    else:
        print("Entry serialization test FAILED")
        exit(1)
