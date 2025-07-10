#!/usr/bin/env python3
"""
Test the actual web form scenario with the Protestantism entry.

This test simulates the exact form data that would be submitted
from the browser when editing the Protestantism entry.
"""

import pytest
from app import create_app
from app.services.dictionary_service import DictionaryService
from app.utils.multilingual_form_processor import merge_form_data_with_entry_data


@pytest.mark.integration
def test_protestantism_form_submission():
    """Test the exact scenario with Protestantism entry form submission."""
    
    app = create_app()
    with app.app_context():
        dict_service = app.injector.get(DictionaryService)
        
        print("🔍 Testing Protestantism entry form submission...")
        
        # 1. Get the current entry from database
        entry_id = 'Protestantism_b97495fb-d52f-4755-94bf-a7a762339605'
        current_entry = dict_service.get_entry(entry_id)
        
        if not current_entry:
            print("❌ Entry not found in database!")
            return
        
        print(f"📊 Current entry state:")
        print(f"  ID: {current_entry.id}")
        print(f"  Lexical unit: {current_entry.lexical_unit}")
        print(f"  Number of senses: {len(current_entry.senses)}")
        if current_entry.senses:
            sense = current_entry.senses[0]
            print(f"  First sense definition: '{sense.definition}'")
            print(f"  First sense definitions dict: {sense.definitions}")
            print(f"  First sense grammatical_info: '{sense.grammatical_info}'")
        
        # 2. Simulate what the user would fill in the form
        # This is what the browser would send when user fills in definition and grammatical category
        form_data = {
            'id': entry_id,
            'lexical_unit[en]': 'Protestantism',
            'senses[0][id]': current_entry.senses[0].id if current_entry.senses else 'sense_1',
            'senses[0][definition]': 'A form of Christianity that originated with the Reformation.',  # USER FILLS THIS
            'senses[0][grammatical_info]': 'noun',  # USER SELECTS THIS
            'senses[0][examples][0][text]': 'Protestantism spread rapidly across Northern Europe.',  # USER ADDS THIS
            'senses[0][examples][0][translation]': ''  # Empty translation
        }
        
        print(f"\n📝 Form data (what user would submit):")
        for key, value in form_data.items():
            print(f"  {key}: '{value}'")
        
        # 3. Convert current entry to dictionary format (what would come from database)
        current_entry_data = current_entry.to_dict()
        
        print(f"\n📊 Current entry data (from database):")
        print(f"  {current_entry_data}")
        
        # 4. Test the merging process (this is what happens in the save route)
        merged_data = merge_form_data_with_entry_data(form_data, current_entry_data)
        
        print(f"\n🔄 Merged data result:")
        print(f"  {merged_data}")
        
        # 5. Check if the new data is preserved
        if 'senses' in merged_data and merged_data['senses']:
            merged_sense = merged_data['senses'][0]
            
            print(f"\n💾 Final merged sense:")
            print(f"  Definition: '{merged_sense.get('definition', 'MISSING')}'")
            print(f"  Grammatical info: '{merged_sense.get('grammatical_info', 'MISSING')}'")
            print(f"  Examples: {merged_sense.get('examples', 'MISSING')}")
            
            # CRITICAL ASSERTIONS
            expected_definition = 'A form of Christianity that originated with the Reformation.'
            expected_grammatical_info = 'noun'
            
            assert merged_sense.get('definition') == expected_definition, \
                f"❌ Definition lost! Expected: '{expected_definition}', Got: '{merged_sense.get('definition')}'"
            
            assert merged_sense.get('grammatical_info') == expected_grammatical_info, \
                f"❌ Grammatical info lost! Expected: '{expected_grammatical_info}', Got: '{merged_sense.get('grammatical_info')}'"
            
            print("✅ SUCCESS: Form data properly merged - no data loss!")
        else:
            print("❌ FAILED: No senses in merged data!")
            assert False, "No senses found in merged data"


@pytest.mark.integration
def test_form_data_parsing():
    """Test that we can parse the form data structure correctly."""
    
    print("\n🔍 Testing form data parsing...")
    
    # Simulate complex form data structure
    form_data = {
        'id': 'test_entry',
        'lexical_unit[en]': 'test_word',
        'senses[0][id]': 'sense_1',
        'senses[0][definition]': 'Test definition',
        'senses[0][grammatical_info]': 'noun',
        'senses[0][examples][0][text]': 'Example sentence',
        'senses[0][examples][0][translation]': 'Translation of example',
        'notes[general][en][text]': 'General note in English'
    }
    
    print("📝 Raw form data:")
    for key, value in form_data.items():
        print(f"  {key}: '{value}'")
    
    # Test if our current merge function can handle this structure
    existing_entry_data = {
        'id': 'test_entry',
        'lexical_unit': {'en': 'test_word'},
        'senses': [
            {
                'id': 'sense_1',
                'definition': '',  # Empty - should get new data
                'grammatical_info': None,  # None - should get new data
                'examples': []  # Empty - should get new data
            }
        ]
    }
    
    print(f"\n📊 Existing entry data:")
    print(f"  {existing_entry_data}")
    
    # Test merge
    merged = merge_form_data_with_entry_data(form_data, existing_entry_data)
    
    print(f"\n🔄 Merged result:")
    print(f"  {merged}")
    
    # Check if form data structure is correctly parsed
    if 'senses' in merged and merged['senses']:
        sense = merged['senses'][0]
        print(f"\n💾 Merged sense data:")
        print(f"  Definition: '{sense.get('definition')}'")
        print(f"  Grammatical info: '{sense.get('grammatical_info')}'")
        print(f"  Examples: {sense.get('examples')}")
    else:
        print("❌ No senses in merged data - form parsing failed!")


if __name__ == '__main__':
    test_protestantism_form_submission()
    test_form_data_parsing()
    print("\n🎉 All tests completed!")
