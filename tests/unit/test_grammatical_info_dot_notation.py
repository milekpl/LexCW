#!/usr/bin/env python3

"""
Unit test for grammatical_info dot notation handling in form processing.
"""

import os
import sys
import pytest

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.utils.multilingual_form_processor import merge_form_data_with_entry_data
from app.models.entry import Entry


def test_grammatical_info_dot_notation_flattening():
    """Test that grammatical_info.part_of_speech is correctly flattened to a string."""
    
    # Test data with dot notation
    form_data = {
        'lexical_unit': {'en': 'test'},
        'grammatical_info.part_of_speech': 'noun',
    }
    
    # Existing entry data
    entry_data = {
        'id': 'test_entry',
        'lexical_unit': {'en': 'test'},
        'senses': [],
        'grammatical_info': ''
    }
    
    # Process the form data
    merged_data = merge_form_data_with_entry_data(form_data, entry_data)
    
    # Check that grammatical_info was flattened to a string
    assert 'grammatical_info' in merged_data
    assert isinstance(merged_data['grammatical_info'], str)
    assert merged_data['grammatical_info'] == 'noun'
    
    # Ensure Entry.from_dict doesn't fail
    entry = Entry.from_dict(merged_data)
    assert entry.grammatical_info == 'noun'


def test_entry_creation_with_dot_notation_grammatical_info():
    """Test that Entry creation doesn't fail with dot notation grammatical_info fields."""
    
    # Simulate real form data with dot notation
    form_data = {
        'lexical_unit': {'en': 'Protestantism'},
        'grammatical_info.part_of_speech': 'noun',
        'senses[0].definition': 'A form of Christianity',
        'senses[0].grammatical_info.part_of_speech': 'noun'
    }
    
    # Simulate existing entry
    entry_data = {
        'id': 'test_id',
        'lexical_unit': {'en': 'Protestantism'},
        'senses': [
            {
                'id': 'sense1',
                'definition': {'en': ''},
                'grammatical_info': ''
            }
        ],
        'grammatical_info': ''
    }
    
    # This should not raise an AttributeError
    merged_data = merge_form_data_with_entry_data(form_data, entry_data)
    entry = Entry.from_dict(merged_data)
    
    # Verify the entry was created successfully
    assert entry.id == 'test_id'
    assert isinstance(entry.grammatical_info, str)
    assert entry.grammatical_info == 'noun'


if __name__ == '__main__':
    test_grammatical_info_dot_notation_flattening()
    test_entry_creation_with_dot_notation_grammatical_info()
    print("✅ All tests passed!")
