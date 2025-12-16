#!/usr/bin/env python3

"""
Test the Entry.from_dict method with grammatical_info that should be flattened
"""

from app.models.entry import Entry
from app.utils.multilingual_form_processor import merge_form_data_with_entry_data

# Test data that simulates the real form submission
form_data = {
    'lexical_unit': {'en': 'Protestantism'},
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


def test_entry_from_dict_with_flattened_grammatical_info() -> None:
    merged_data = merge_form_data_with_entry_data(form_data, entry_data)
    assert isinstance(merged_data, dict)
    entry = Entry.from_dict(merged_data)
    assert entry is not None
