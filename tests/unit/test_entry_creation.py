#!/usr/bin/env python3

"""
Test the Entry.from_dict method with grammatical_info that should be flattened
"""

import os
import sys

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.models.entry import Entry
from app.utils.multilingual_form_processor import merge_form_data_with_entry_data

# Test data that simulates the real form submission
form_data = {
    'lexical_unit': 'Protestantism',
    'grammatical_info.part_of_speech': 'noun',  # This is what causes the issue
    'senses[0].definition': 'A form of Christianity',
    'senses[0].grammatical_info.part_of_speech': 'noun'  # Sense-level grammatical info
}

# Simulate existing entry data
entry_data = {
    'id': 'Protestantism_b97495fb-d52f-4755-94bf-a7a762339605',
    'lexical_unit': {'en': 'Protestantism'},
    'senses': [
        {
            'id': 'sense1',
            'definition': {'en': ''},  # Empty definition
            'grammatical_info': ''
        }
    ],
    'grammatical_info': ''
}

print("Testing the exact scenario that caused the error...")
print(f"Form data contains grammatical_info.part_of_speech: {form_data.get('grammatical_info.part_of_speech')}")

# This is what happens in the edit_entry view
merged_data = merge_form_data_with_entry_data(form_data, entry_data)
print(f"Merged data grammatical_info: {merged_data.get('grammatical_info')} ({type(merged_data.get('grammatical_info'))})")

# This is where the error occurred
try:
    entry = Entry.from_dict(merged_data)
    print("✅ Entry.from_dict succeeded!")
    print(f"Entry grammatical_info: {entry.grammatical_info} ({type(entry.grammatical_info)})")
except Exception as e:
    print(f"❌ Entry.from_dict failed: {e}")
    import traceback
    traceback.print_exc()
