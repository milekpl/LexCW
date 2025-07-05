#!/usr/bin/env python3

"""
Debug script to test the grammatical_info flattening in merge_form_data_with_entry_data
"""

import os
import sys

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.utils.multilingual_form_processor import merge_form_data_with_entry_data

# Test case: form data with nested grammatical_info structure
form_data = {
    'lexical_unit': 'Protestantism',
    'senses[0].definition': 'A form of Christianity',
    'senses[0].grammatical_info.part_of_speech': 'noun',
    'grammatical_info.part_of_speech': 'noun'  # Add entry-level grammatical info
}

# Existing entry data (simulating what comes from database)
entry_data = {
    'id': 'test_entry',
    'lexical_unit': {'en': 'Protestantism'},
    'senses': [
        {
            'id': 'sense1',
            'definition': {'en': 'Original definition'},
            'grammatical_info': 'noun'  # This is a string in existing data
        }
    ],
    'grammatical_info': ''  # Empty in entry level
}

print("Form data:")
for k, v in form_data.items():
    print(f"  {k}: {v} ({type(v)})")

print("\nEntry data:")
for k, v in entry_data.items():
    print(f"  {k}: {v} ({type(v)})")

print("\nCalling merge_form_data_with_entry_data...")
merged_data = merge_form_data_with_entry_data(form_data, entry_data)

print("\nMerged data:")
for k, v in merged_data.items():
    print(f"  {k}: {v} ({type(v)})")

print(f"\nFinal grammatical_info: '{merged_data.get('grammatical_info')}' ({type(merged_data.get('grammatical_info'))})")
