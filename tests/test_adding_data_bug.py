#!/usr/bin/env python3
"""
Test to reproduce the specific issue: adding data to previously empty fields.

User scenario:
1. Entry exists with NO definition
2. User fills in the definition field
3. User adds grammatical category
4. User saves
5. NO DATA RETAINED - this is the bug!
"""

import pytest
from app import create_app
from app.models.entry import Entry
from app.utils.multilingual_form_processor import merge_form_data_with_entry_data


class TestAddingDataToEmptyFields:
    """Test the specific case of adding data to previously empty fields."""

    @pytest.fixture
    def app(self):
        """Create test app instance."""
        app = create_app()
        app.config['TESTING'] = True
        return app

    def test_adding_definition_to_empty_field(self, app):
        """
        CRITICAL TEST: Adding data to previously empty fields should work.
        
        This reproduces the user's exact scenario:
        1. Entry with empty/no definition
        2. User fills definition + grammatical category
        3. Form submits new data
        4. Data should be saved, NOT lost
        """
        with app.app_context():
            
            print("🔍 Testing: Adding definition to previously empty field")
            
            # 1. Original entry with NO definition (empty database state)
            original_entry_data = {
                'id': 'test_empty_definition',
                'lexical_unit': {'en': 'emptyword'},
                'senses': [
                    {
                        'id': 'sense1',
                        # NO definition field at all, or empty definition
                        'grammatical_info': None  # Also empty
                    }
                ]
            }
            
            print(f"📊 Original entry: {original_entry_data}")
            
            # 2. User fills in definition and grammatical category, form submits this
            form_data_with_new_content = {
                'id': 'test_empty_definition', 
                'lexical_unit': {'en': 'emptyword'},
                'senses': [
                    {
                        'id': 'sense1',
                        'definition': 'NEW definition added by user',  # USER ADDED THIS
                        'grammatical_info': 'noun'  # USER ADDED THIS
                    }
                ]
            }
            
            print(f"📝 Form data (what user entered): {form_data_with_new_content}")
            
            # 3. Test the merging process (this is what happens in views.py)
            merged_data = merge_form_data_with_entry_data(form_data_with_new_content, original_entry_data)
            
            print(f"🔄 Merged data: {merged_data}")
            
            # 4. Create entry from merged data
            final_entry = Entry(**merged_data)
            
            print(f"💾 Final entry definition: {final_entry.senses[0].definitions}")
            print(f"💾 Final entry grammatical_info: {final_entry.senses[0].grammatical_info}")
            
            # 5. CRITICAL ASSERTIONS: New data should be saved
            expected_definition = {'en': {'text': 'NEW definition added by user'}}  # Expected format in Entry model
            # Should always be nested dict format
            assert final_entry.senses[0].definitions == expected_definition, \
                f"NEW definition was not saved! Got definitions: {final_entry.senses[0].definitions}"
            
            assert final_entry.senses[0].grammatical_info == 'noun', \
                f"NEW grammatical_info was not saved! Got: {final_entry.senses[0].grammatical_info}"
            
            print("✅ SUCCESS: New data should be preserved!")

    def test_adding_definition_string_vs_dict_format(self, app):
        """
        Test the format handling for definitions.
        
        JavaScript might send definition as string, but Entry model expects dict format.
        """
        with app.app_context():
            
            print("\n🔍 Testing: Definition format handling (string vs dict)")
            
            # Original entry with no definition
            original_entry_data = {
                'id': 'test_format',
                'lexical_unit': {'en': 'formattest'},
                'senses': [{'id': 'sense1'}]  # Completely empty sense
            }
            
            # Form might send definition as string (from textarea)
            form_data_string_definition = {
                'id': 'test_format',
                'lexical_unit': {'en': 'formattest'},
                'senses': [
                    {
                        'id': 'sense1',
                        'definition': 'Simple string definition'  # String format
                    }
                ]
            }
            
            print(f"📊 Original: {original_entry_data}")
            print(f"📝 Form (string def): {form_data_string_definition}")
            
            # Test merging
            merged_data = merge_form_data_with_entry_data(form_data_string_definition, original_entry_data)
            
            print(f"🔄 Merged: {merged_data}")
            
            # Create entry
            final_entry = Entry(**merged_data)
            
            print(f"💾 Final definitions: {final_entry.senses[0].definitions}")
            print(f"💾 Final definition property: {final_entry.senses[0].definition}")
            
            # String should be normalized to nested dict format
            assert final_entry.senses[0].definitions == {'en': {'text': 'Simple string definition'}}, \
                f"Definition not normalized correctly! Got: {final_entry.senses[0].definitions}"


if __name__ == '__main__':
    pytest.main([__file__, '-v', '-s'])
