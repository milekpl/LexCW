#!/usr/bin/env python3
"""
Test ID auto-generation in Entry and Sense objects.
"""

import sys
import os
sys.path.insert(0, os.path.abspath('.'))

from app.models.entry import Entry
from app.models.sense import Sense

def test_id_generation():
    """Test that Entry and Sense auto-generate IDs when not provided."""
    print("=== Testing ID Auto-Generation ===")
    
    # Test Sense ID generation
    sense_data = {
        'definition': 'Test definition',
        'gloss': 'Test gloss'
    }
    
    sense = Sense(**sense_data)
    print(f"Sense created with auto-generated ID: {sense.id}")
    print(f"Sense to_dict: {sense.to_dict()}")
    
    # Test Entry ID generation
    entry_data = {
        'lexical_unit': {'seh': 'testword'},
        'senses': [sense_data]
    }
    
    entry = Entry(**entry_data)
    print(f"\nEntry created with auto-generated ID: {entry.id}")
    print(f"Entry senses: {[s.id for s in entry.senses]}")
    print(f"Entry to_dict: {entry.to_dict()}")

if __name__ == '__main__':
    test_id_generation()
