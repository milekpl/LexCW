#!/usr/bin/env python3
"""
Comprehensive test for the "adding data to empty fields" scenario.

This test specifically targets the bug where:
1. Entry starts with empty Definition field
2. User fills Definition + adds grammatical category
3. Save results in NO DATA RETAINED

Edge cases to test:
- Empty string vs None vs missing field
- Form data with new content vs empty content
- Mixed scenarios (some existing, some new)
"""

from typing import Dict, Any, List
from app.utils.multilingual_form_processor import _merge_senses_data


def test_empty_to_filled_scenario():
    """
    CRITICAL: Test the exact user scenario that was failing.
    
    User reported: Start with empty Definition, fill it + add grammatical category,
    saving results in NO DATA RETAINED.
    """
    
    print("🔍 Testing: Empty to filled scenario (the reported bug)")
    
    # 1. Existing sense with empty/no definition (various empty states)
    existing_senses = [
        {
            'id': 'sense-1',
            'definitions': {},         # Empty dict for multitext
            'grammatical_info': None, # None value  
            'examples': [],          # Empty list
            'glosses': {},           # Empty dict
            'notes': {}              # Empty dict
        }
    ]

    # 2. Form data with NEW content filled by user
    form_senses = [
        {
            'id': 'sense-1',
            'definitions': {'en': {'text': 'User typed this new definition'}},  # NEW CONTENT
            'grammatical_info': 'noun',                      # NEW CONTENT
            'examples': [{'text': 'New example', 'translation': 'New translation'}],  # NEW CONTENT
            'glosses': {'en': {'text': 'house'}, 'pt': {'text': 'casa'}},        # NEW CONTENT
            'notes': {'general': {'en': 'User note'}}        # NEW CONTENT
        }
    ]
    
    # 3. Merge
    merged_senses = _merge_senses_data(form_senses, existing_senses)
    
    # 4. VERIFY: New content should be RETAINED, not lost
    assert len(merged_senses) == 1
    merged_sense = merged_senses[0]
    
    # All new data should be preserved
    assert merged_sense['definitions']['en']['text'] == 'User typed this new definition', \
        f"❌ NEW definition lost! Got: '{merged_sense.get('definitions')}'"
    
    assert merged_sense['grammatical_info'] == 'noun', \
        f"❌ NEW grammatical_info lost! Got: '{merged_sense.get('grammatical_info')}'"
        
    assert merged_sense['examples'] == [{'text': 'New example', 'translation': 'New translation'}], \
        f"❌ NEW examples lost! Got: {merged_sense.get('examples')}"
    
    assert merged_sense['glosses'] == {'en': {'text': 'house'}, 'pt': {'text': 'casa'}}, \
        f"❌ NEW glosses lost! Got: {merged_sense.get('glosses')}"
    
    assert merged_sense['notes'] == {'general': {'en': 'User note'}}, \
        f"❌ NEW notes lost! Got: {merged_sense.get('notes')}"
    
    print("✅ SUCCESS: New data properly retained when adding to empty fields")


def test_whitespace_only_to_content():
    """Test the case where existing field has only whitespace."""
    
    print("\n🔍 Testing: Whitespace-only to real content")
    
    # Existing with whitespace-only content
    existing_senses = [
        {
            'id': 'sense-1',
            'definitions': {'en': {'text': '   \n\t  '}},    # Whitespace-only multitext
            'grammatical_info': ' ',       # Space-only
        }
    ]

    # Form with real content
    form_senses = [
        {
            'id': 'sense-1',
            'definitions': {'en': {'text': 'Real definition content'}},
            'grammatical_info': 'verb',
        }
    ]
    
    merged_senses = _merge_senses_data(form_senses, existing_senses)
    merged_sense = merged_senses[0]
    
    # Should use new content (form data) over whitespace-only existing data
    assert merged_sense['definitions']['en']['text'] == 'Real definition content'
    assert merged_sense['grammatical_info'] == 'verb'
    
    print("✅ SUCCESS: Whitespace-only data correctly replaced with real content")


def test_none_vs_empty_string_vs_missing():
    """Test different ways a field can be 'empty'."""
    
    print("\n🔍 Testing: None vs empty string vs missing field")
    
    # Test all empty states
    test_cases = [
        # Case 1: None values
        {
            'existing': {'id': 'sense-1', 'definitions': None, 'grammatical_info': None},
            'form': {'id': 'sense-1', 'definitions': {'en': {'text': 'New def'}}, 'grammatical_info': 'noun'},
            'case_name': 'None values'
        },
        # Case 2: Empty dict
        {
            'existing': {'id': 'sense-1', 'definitions': {}, 'grammatical_info': ''},
            'form': {'id': 'sense-1', 'definitions': {'en': {'text': 'New def'}}, 'grammatical_info': 'noun'},
            'case_name': 'Empty dict'
        },
        # Case 3: Missing fields entirely
        {
            'existing': {'id': 'sense-1'},  # Fields don't exist
            'form': {'id': 'sense-1', 'definitions': {'en': {'text': 'New def'}}, 'grammatical_info': 'noun'},
            'case_name': 'Missing fields'
        }
    ]
    
    for case in test_cases:
        print(f"  📝 Testing: {case['case_name']}")
        
        merged_senses = _merge_senses_data([case['form']], [case['existing']])
        merged_sense = merged_senses[0]
        
        # Should always use new content from form
        assert merged_sense['definitions']['en']['text'] == 'New def', \
            f"Failed for {case['case_name']}: definitions = {merged_sense.get('definitions')}"
        assert merged_sense['grammatical_info'] == 'noun', \
            f"Failed for {case['case_name']}: grammatical_info = {merged_sense.get('grammatical_info')}"
        
        print(f"    ✅ {case['case_name']}: PASS")


def test_preserve_existing_when_form_empty():
    """Test that we still preserve existing data when form fields are empty."""
    
    print("\n🔍 Testing: Preserve existing when form is empty")
    
    # Existing with good data
    existing_senses = [
        {
            'id': 'sense-1',
            'definitions': {'en': {'text': 'Important existing definition'}},
            'grammatical_info': 'adjective',
            'examples': [{'text': 'Old example', 'translation': 'Old trans'}]
        }
    ]

    # Form with missing/empty fields (user didn't change these)
    form_senses = [
        {
            'id': 'sense-1',
            # definitions missing - should preserve existing
            # grammatical_info missing - should preserve existing
            # examples missing - should preserve existing
            'notes': {'general': {'en': 'New note'}}  # Only this is new
        }
    ]
    
    merged_senses = _merge_senses_data(form_senses, existing_senses)
    merged_sense = merged_senses[0]
    
    # Should preserve existing data for missing fields
    assert merged_sense['definitions']['en']['text'] == 'Important existing definition'
    assert merged_sense['grammatical_info'] == 'adjective'
    assert merged_sense['examples'] == [{'text': 'Old example', 'translation': 'Old trans'}]
    
    # Should add new data
    assert merged_sense['notes'] == {'general': {'en': 'New note'}}
    
    print("✅ SUCCESS: Existing data preserved when form fields are empty")


def test_edge_case_form_explicitly_empty():
    """Test when form explicitly sends empty values (not missing fields)."""
    
    print("\n🔍 Testing: Form explicitly sends empty values")
    
    # Existing with data
    existing_senses = [
        {
            'id': 'sense-1',
            'definitions': {'en': {'text': 'Existing definition'}},
            'grammatical_info': 'noun'
        }
    ]

    # Form explicitly sends empty values (user cleared the fields)
    form_senses = [
        {
            'id': 'sense-1',
            'definitions': {},  # User explicitly cleared this (empty dict)
            'grammatical_info': '',  # User explicitly cleared this
            'notes': {'general': {'en': 'But added a note'}}  # User added this
        }
    ]
    
    merged_senses = _merge_senses_data(form_senses, existing_senses)
    merged_sense = merged_senses[0]
    
    # Empty form fields should preserve existing data (no data loss)
    assert merged_sense['definitions']['en']['text'] == 'Existing definition'
    assert merged_sense['grammatical_info'] == 'noun'
    
    # New data should be added
    assert merged_sense['notes'] == {'general': {'en': 'But added a note'}}
    
    print("✅ SUCCESS: Empty form values don't cause data loss")


if __name__ == '__main__':
    print("🚀 Running comprehensive test for adding data to empty fields...\n")
    
    test_empty_to_filled_scenario()
    test_whitespace_only_to_content()
    test_none_vs_empty_string_vs_missing()
    test_preserve_existing_when_form_empty()
    test_edge_case_form_explicitly_empty()
    
    print("\n🎉 All tests passed! The 'adding data to empty fields' bug appears to be fixed.")
