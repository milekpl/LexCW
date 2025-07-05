#!/usr/bin/env python3
"""
Debug script to simulate the exact Protestant(2) form saving scenario.
"""

from app.models.entry import Entry


def test_protestant_scenario():
    """Test the exact Protestant(2) scenario that's causing issues."""
    
    print("=== Testing Protestant(2) Form Saving Scenario ===")
    
    # Simulate the original entry data (what would be loaded from LIFT)
    original_data = {
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
    
    print("1. Creating original entry...")
    original_entry = Entry(**original_data)
    print(f"   Entry POS: {original_entry.grammatical_info}")
    print(f"   Sense POS: {original_entry.senses[0].grammatical_info}")
    
    # Simulate form data being submitted (what might come from the web form)
    # This represents what would be in the merged_data after form processing
    form_data = {
        'id': 'Protestant_2',
        'lexical_unit': {'en': 'Protestant'},
        'homograph_number': 2,
        'grammatical_info': '',  # Form sends empty string instead of None
        'senses': [
            {
                'id': 'Protestant_2_s1',
                'definition': {'en': 'A member of a Protestant church'},
                'grammatical_info': 'noun',  # This should be preserved
                'glosses': [{'lang': 'en', 'text': 'Protestant person'}]
            }
        ]
    }
    
    print("\n2. Creating entry from form data...")
    form_entry = Entry(**form_data)
    print(f"   Entry POS: {form_entry.grammatical_info}")
    print(f"   Sense POS: {form_entry.senses[0].grammatical_info}")
    
    # Check if the sense POS was preserved
    if form_entry.senses[0].grammatical_info != 'noun':
        print("❌ BUG FOUND: Sense grammatical_info was cleared!")
        print(f"   Expected: 'noun', Got: {form_entry.senses[0].grammatical_info}")
        return False
    else:
        print("✅ Sense grammatical_info preserved correctly")
        return True


def test_empty_vs_none_entry_pos():
    """Test difference between None and empty string for entry POS."""
    
    print("\n=== Testing Empty String vs None for Entry POS ===")
    
    # Test with None
    data_none = {
        'id': 'test1',
        'lexical_unit': {'en': 'test'},
        'grammatical_info': None,
        'senses': [{'id': 's1', 'definition': {'en': 'test'}, 'grammatical_info': 'noun'}]
    }
    
    entry_none = Entry(**data_none)
    print(f"None POS - Entry: {entry_none.grammatical_info}, Sense: {entry_none.senses[0].grammatical_info}")
    
    # Test with empty string
    data_empty = {
        'id': 'test2',
        'lexical_unit': {'en': 'test'},
        'grammatical_info': '',
        'senses': [{'id': 's2', 'definition': {'en': 'test'}, 'grammatical_info': 'noun'}]
    }
    
    entry_empty = Entry(**data_empty)
    print(f"Empty POS - Entry: {entry_empty.grammatical_info}, Sense: {entry_empty.senses[0].grammatical_info}")


if __name__ == '__main__':
    success = test_protestant_scenario()
    test_empty_vs_none_entry_pos()
    
    if not success:
        print("\n❌ Issue reproduced!")
        exit(1)
    else:
        print("\n✅ No issue found in Entry model")
