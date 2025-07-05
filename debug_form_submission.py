#!/usr/bin/env python3
"""
Debug script to test form submission data processing.

This script simulates the exact form submission that might be causing 
the grammatical category clearing issue.
"""

from app.models.entry import Entry
from app.utils.multilingual_form_processor import merge_form_data_with_entry_data


def test_form_submission_scenario():
    """Test form submission data processing scenario."""
    
    print("=== Testing Form Submission Data Processing ===")
    
    # Simulate the existing entry data (what would be in the database)
    existing_entry_data = {
        'id': 'Protestant_2',
        'lexical_unit': {'en': 'Protestant'},
        'homograph_number': 2,
        'grammatical_info': None,  # Entry has no POS
        'senses': [
            {
                'id': 'Protestant_2_s1',
                'definition': {'en': 'A member of a Protestant church'},
                'grammatical_info': 'noun',  # Sense HAS POS
                'glosses': [{'lang': 'en', 'text': 'Protestant person'}]
            }
        ]
    }
    
    # Simulate form data as it might come from the web form
    # This simulates what request.get_json() would return
    form_data = {
        'id': 'Protestant_2',
        'lexical_unit': {'en': 'Protestant'},
        'homograph_number': 2,
        'grammatical_info': '',  # Empty string from form
        'senses': [
            {
                'id': 'Protestant_2_s1',
                'definition': {'en': 'A member of a Protestant church'},
                'grammatical_info': 'noun',  # This should be preserved!
                'glosses': [{'lang': 'en', 'text': 'Protestant person'}]
            }
        ]
    }
    
    print("1. Existing entry data:")
    existing_entry = Entry(**existing_entry_data)
    print(f"   Entry POS: {existing_entry.grammatical_info}")
    print(f"   Sense POS: {existing_entry.senses[0].grammatical_info}")
    
    print("\n2. Form data received:")
    print(f"   Entry POS from form: '{form_data['grammatical_info']}'")
    print(f"   Sense POS from form: '{form_data['senses'][0]['grammatical_info']}'")
    
    # Simulate the merge process that happens in views.py
    print("\n3. Merging form data with existing entry data...")
    merged_data = merge_form_data_with_entry_data(form_data, existing_entry_data)
    print(f"   Merged entry POS: '{merged_data.get('grammatical_info', 'NOT_SET')}'")
    print(f"   Merged sense POS: '{merged_data['senses'][0]['grammatical_info']}'")
    
    # Simulate creating Entry from merged data (what happens in views.py)
    print("\n4. Creating Entry from merged data...")
    new_entry = Entry(**merged_data)
    print(f"   Final entry POS: {new_entry.grammatical_info}")
    print(f"   Final sense POS: {new_entry.senses[0].grammatical_info}")
    
    # Check if the issue occurred
    if new_entry.senses[0].grammatical_info != 'noun':
        print("\n❌ BUG REPRODUCED: Sense grammatical_info was cleared!")
        print(f"   Expected: 'noun', Got: '{new_entry.senses[0].grammatical_info}'")
        return False
    else:
        print("\n✅ Sense grammatical_info preserved correctly")
        return True


def test_different_form_data_formats():
    """Test different ways form data might be structured."""
    
    print("\n=== Testing Different Form Data Formats ===")
    
    base_existing_data = {
        'id': 'test',
        'lexical_unit': {'en': 'test'},
        'grammatical_info': None,
        'senses': [
            {
                'id': 'test_s1',
                'definition': {'en': 'test'},
                'grammatical_info': 'noun'
            }
        ]
    }
    
    # Test case 1: Empty string for entry POS
    form_data_1 = {
        'grammatical_info': '',
        'senses': [{'id': 'test_s1', 'grammatical_info': 'noun'}]
    }
    merged_1 = merge_form_data_with_entry_data(form_data_1, base_existing_data)
    entry_1 = Entry(**merged_1)
    print(f"Test 1 - Empty string entry POS: {entry_1.senses[0].grammatical_info}")
    
    # Test case 2: None for entry POS
    form_data_2 = {
        'grammatical_info': None,
        'senses': [{'id': 'test_s1', 'grammatical_info': 'noun'}]
    }
    merged_2 = merge_form_data_with_entry_data(form_data_2, base_existing_data)
    entry_2 = Entry(**merged_2)
    print(f"Test 2 - None entry POS: {entry_2.senses[0].grammatical_info}")
    
    # Test case 3: Missing entry POS key
    form_data_3 = {
        'senses': [{'id': 'test_s1', 'grammatical_info': 'noun'}]
    }
    merged_3 = merge_form_data_with_entry_data(form_data_3, base_existing_data)
    entry_3 = Entry(**merged_3)
    print(f"Test 3 - Missing entry POS key: {entry_3.senses[0].grammatical_info}")


if __name__ == '__main__':
    success = test_form_submission_scenario()
    test_different_form_data_formats()
    
    if not success:
        print("\n❌ Issue reproduced in form submission processing!")
        exit(1)
    else:
        print("\n✅ No issue found in form submission processing")
