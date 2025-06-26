#!/usr/bin/env python3

"""
Debug entry creation issue - focus on LIFT generation
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.models.entry import Entry
from app.models.sense import Sense
from app.parsers.lift_parser import LIFTParser

# Test data
test_data = {
    "lexical_unit": {"en": "test_word"},
    "senses": [
        {
            "id": "sense1",
            "definitions": {"en": "A test definition"},
            "grammatical_info": "noun"
        }
    ]
}

print("Test data:", test_data)

try:
    print("\n=== Testing Entry creation ===")
    entry = Entry.from_dict(test_data)
    print("Entry created successfully:", entry)
    print("Entry senses:", entry.senses)
    if entry.senses:
        print("First sense grammatical_info:", entry.senses[0].grammatical_info)
        print("First sense type:", type(entry.senses[0]))
    
    print("\n=== Testing LIFT generation ===")
    lift_parser = LIFTParser()
    lift_xml = lift_parser.generate_lift_string([entry])
    print("LIFT XML generated successfully")
    print("First 500 chars:", lift_xml[:500])

except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
