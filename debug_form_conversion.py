#!/usr/bin/env python3
"""
Test to debug the exact form data conversion issue.

This test simulates what might happen when the JavaScript form
converter processes the sense grammatical_info fields.
"""

from app.models.entry import Entry
from app.utils.multilingual_form_processor import merge_form_data_with_entry_data


def test_javascript_form_conversion_issue():
    """Test form data conversion as it might happen in JavaScript."""
    
    print("=== Testing JavaScript Form Data Conversion Issue ===")
    
    # Simulate what the existing entry might look like in the database
    existing_entry_data = {
        'id': 'Protestant_2',
        'lexical_unit': {'en': 'Protestant'},
        'homograph_number': 2,
        'grammatical_info': None,  # No entry-level POS
        'senses': [
            {
                'id': 'Protestant_2_s1',
                'definition': {'en': 'A member of a Protestant church'},
                'grammatical_info': 'noun',  # Sense has POS - this should be preserved!
                'glosses': [{'lang': 'en', 'text': 'Protestant person'}]
            }
        ]
    }
    
    print("1. Original entry from database:")
    original_entry = Entry(**existing_entry_data)
    print(f"   Entry POS: {original_entry.grammatical_info}")
    print(f"   Sense POS: {original_entry.senses[0].grammatical_info}")
    
    # Simulate different possible form data structures that might come from JS
    
    # Scenario 1: Complete sense data preserved
    form_data_good = {
        'id': 'Protestant_2',
        'lexical_unit': {'en': 'Protestant'},
        'homograph_number': 2,
        'grammatical_info': '',  # Entry POS empty (comes from form)
        'senses': [
            {
                'id': 'Protestant_2_s1',
                'definition': {'en': 'A member of a Protestant church'},
                'grammatical_info': 'noun',  # Sense POS preserved
                'glosses': [{'lang': 'en', 'text': 'Protestant person'}]
            }
        ]
    }
    
    # Scenario 2: Sense data missing grammatical_info (possible bug)
    form_data_bad = {
        'id': 'Protestant_2',
        'lexical_unit': {'en': 'Protestant'},
        'homograph_number': 2,
        'grammatical_info': '',  # Entry POS empty
        'senses': [
            {
                'id': 'Protestant_2_s1',
                'definition': {'en': 'A member of a Protestant church'},
                # Missing grammatical_info! This could be the bug
                'glosses': [{'lang': 'en', 'text': 'Protestant person'}]
            }
        ]
    }
    
    # Scenario 3: Sense grammatical_info is empty string instead of missing
    form_data_empty = {
        'id': 'Protestant_2',
        'lexical_unit': {'en': 'Protestant'},
        'homograph_number': 2,
        'grammatical_info': '',  # Entry POS empty
        'senses': [
            {
                'id': 'Protestant_2_s1',
                'definition': {'en': 'A member of a Protestant church'},
                'grammatical_info': '',  # Empty string instead of 'noun'
                'glosses': [{'lang': 'en', 'text': 'Protestant person'}]
            }
        ]
    }
    
    print("\n2. Testing scenario 1 (good data):")
    merged_good = merge_form_data_with_entry_data(form_data_good, existing_entry_data)
    entry_good = Entry(**merged_good)
    print(f"   Result - Entry POS: {entry_good.grammatical_info}, Sense POS: {entry_good.senses[0].grammatical_info}")
    
    print("\n3. Testing scenario 2 (missing sense grammatical_info):")
    merged_bad = merge_form_data_with_entry_data(form_data_bad, existing_entry_data)
    entry_bad = Entry(**merged_bad)
    sense_pos = getattr(entry_bad.senses[0], 'grammatical_info', 'MISSING_ATTR')
    print(f"   Result - Entry POS: {entry_bad.grammatical_info}, Sense POS: {sense_pos}")
    
    print("\n4. Testing scenario 3 (empty sense grammatical_info):")
    merged_empty = merge_form_data_with_entry_data(form_data_empty, existing_entry_data)
    entry_empty = Entry(**merged_empty)
    print(f"   Result - Entry POS: {entry_empty.grammatical_info}, Sense POS: {entry_empty.senses[0].grammatical_info}")
    
    # Check which scenarios cause the issue
    issues_found = []
    
    if entry_good.senses[0].grammatical_info != 'noun':
        issues_found.append("Scenario 1 (good data)")
    
    if not hasattr(entry_bad.senses[0], 'grammatical_info') or entry_bad.senses[0].grammatical_info != 'noun':
        issues_found.append("Scenario 2 (missing sense grammatical_info)")
    
    if entry_empty.senses[0].grammatical_info != 'noun':
        issues_found.append("Scenario 3 (empty sense grammatical_info)")
    
    if issues_found:
        print(f"\n❌ Issues found in: {', '.join(issues_found)}")
        return False
    else:
        print(f"\n✅ All scenarios preserved sense grammatical_info correctly")
        return True


def test_sense_data_structure():
    """Test how the Sense model handles missing grammatical_info."""
    
    print("\n=== Testing Sense Data Structure Handling ===")
    
    from app.models.sense import Sense
    
    # Test 1: Sense with explicit grammatical_info
    sense_with_pos = Sense(
        id='test_sense_1',
        definition={'en': 'test definition'},
        grammatical_info='noun'
    )
    print(f"Sense with POS: {sense_with_pos.grammatical_info}")
    
    # Test 2: Sense without grammatical_info 
    sense_without_pos = Sense(
        id='test_sense_2',
        definition={'en': 'test definition'}
        # No grammatical_info provided
    )
    print(f"Sense without POS: {getattr(sense_without_pos, 'grammatical_info', 'ATTR_MISSING')}")
    
    # Test 3: Sense with empty string grammatical_info
    sense_empty_pos = Sense(
        id='test_sense_3',
        definition={'en': 'test definition'},
        grammatical_info=''
    )
    print(f"Sense with empty POS: '{sense_empty_pos.grammatical_info}'")


if __name__ == '__main__':
    success = test_javascript_form_conversion_issue()
    test_sense_data_structure()
    
    if not success:
        print("\n❌ Issue found in form data conversion!")
        exit(1)
    else:
        print("\n✅ No issues found in form data conversion")
