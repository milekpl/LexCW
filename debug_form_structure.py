#!/usr/bin/env python3
"""
Debug script to understand the exact data structure being sent by the JavaScript form.

This will help identify if there's a mismatch between what the JavaScript sends
and what our merge function expects.
"""

from app.utils.multilingual_form_processor import merge_form_data_with_entry_data


def test_javascript_form_structure():
    """Test the exact structure that JavaScript would send."""
    
    print("Testing JavaScript form data structure...")
    
    # This is what JavaScript might send based on form field names like:
    # senses[0].definition, senses[0].grammatical_info, etc.
    javascript_form_data = {
        'id': 'test_entry',
        'lexical_unit': {'en': 'testword'},
        'senses': [
            {
                'id': 'sense1',
                'definition': 'User-entered definition',  # This should be preserved
                'grammatical_info': 'noun'
            }
        ]
    }
    
    # Original entry data (from database)
    original_entry_data = {
        'id': 'test_entry',
        'lexical_unit': {'en': 'testword'},
        'senses': [
            {
                'id': 'sense1',
                'definition': {'en': 'Original multilingual definition'},
                'grammatical_info': 'noun',
                'examples': [
                    {'id': 'ex1', 'content': {'en': 'Original example'}}
                ]
            }
        ]
    }
    
    print(f"JavaScript sends: {javascript_form_data}")
    print(f"Original data: {original_entry_data}")
    
    # Test merging
    merged_data = merge_form_data_with_entry_data(javascript_form_data, original_entry_data)
    
    print(f"Merged result: {merged_data}")
    
    # Check what happened to definition
    merged_definition = merged_data['senses'][0].get('definition')
    print(f"Final definition: {merged_definition}")
    
    # The issue might be: JavaScript sends string, but original is dict
    # Our merge function might not handle this correctly
    

def test_missing_definition_case():
    """Test when JavaScript doesn't send definition field at all."""
    
    print("\n" + "="*50)
    print("Testing missing definition case...")
    
    # JavaScript sends form without definition (user didn't edit it)
    javascript_form_data_no_definition = {
        'id': 'test_entry',
        'lexical_unit': {'en': 'testword'},
        'senses': [
            {
                'id': 'sense1',
                # Definition missing - this is the critical case
                'grammatical_info': 'noun'
            }
        ]
    }
    
    # Original entry data (from database)
    original_entry_data = {
        'id': 'test_entry',
        'lexical_unit': {'en': 'testword'},
        'senses': [
            {
                'id': 'sense1',
                'definition': {'en': 'Original definition that MUST be preserved'},
                'grammatical_info': 'noun',
                'examples': [
                    {'id': 'ex1', 'content': {'en': 'Original example'}}
                ]
            }
        ]
    }
    
    print(f"JavaScript sends (no definition): {javascript_form_data_no_definition}")
    print(f"Original data: {original_entry_data}")
    
    # Test merging
    merged_data = merge_form_data_with_entry_data(javascript_form_data_no_definition, original_entry_data)
    
    print(f"Merged result: {merged_data}")
    
    # Check if definition was preserved
    merged_definition = merged_data['senses'][0].get('definition')
    print(f"Final definition: {merged_definition}")
    
    if merged_definition == {'en': 'Original definition that MUST be preserved'}:
        print("✅ SUCCESS: Definition preserved when missing from form!")
    else:
        print("❌ FAILURE: Definition was lost!")


if __name__ == "__main__":
    test_javascript_form_structure()
    test_missing_definition_case()
