#!/usr/bin/env python3
"""
Test the exact form submission flow that the web application uses.

This test simulates what happens when a user edits an entry and submits
the form, ensuring that the merge_form_data_with_entry_data function
works correctly in the real application flow.
"""

import pytest
from app import create_app
from app.models.entry import Entry
from app.utils.multilingual_form_processor import merge_form_data_with_entry_data



@pytest.mark.integration
class TestRealWebFormSubmission:
    """Test the actual web form submission flow."""

    @pytest.fixture
    def app(self):
        """Create test app instance."""
        app = create_app()
        app.config['TESTING'] = True
        return app

    @pytest.mark.integration
    def test_web_form_definition_preservation(self, app):
        """
        Test that exactly mimics what happens when user submits web form.
        
        This reproduces the user's issue: add definition, save, definition disappears.
        """
        with app.app_context():
            
            # 1. Original entry data (what would be in database)
            original_entry_data = {
                'id': 'test_web_entry',
                'lexical_unit': {'en': 'testword'},
                'senses': [
                    {
                        'id': 'sense1',
                        'definition': {'en': 'Original definition that should be preserved'},
                        'grammatical_info': 'noun'
                    }
                ]
            }
            
            # 2. Simulate what JavaScript sends when user submits form
            # This mimics the exact structure that entry-form.js creates
            form_submission_data = {
                'id': 'test_web_entry',
                'lexical_unit': {'en': 'testword'},
                'senses': [
                    {
                        'id': 'sense1',
                        # The issue: JavaScript might not include definition if user didn't edit it
                        # or if there's a bug in form serialization
                    }
                ]
            }
            
            print(f"Original definition: {original_entry_data['senses'][0].get('definition')}")
            print(f"Form data definition: {form_submission_data['senses'][0].get('definition', 'MISSING!')}")
            
            # 3. Test the merging process (this is what happens in views.py)
            merged_data = merge_form_data_with_entry_data(form_submission_data, original_entry_data)
            
            # 4. Create entry from merged data (this is what happens in views.py)
            final_entry = Entry(**merged_data)
            
            print(f"Final entry definition: {final_entry.senses[0].definitions}")
            print(f"Final entry definition property: {final_entry.senses[0].definition}")
            
            # 5. CRITICAL TEST: Definition should be preserved
            assert final_entry.senses[0].definitions == {'en': 'Original definition that should be preserved'}, \
                f"Definition was lost! Got: {final_entry.senses[0].definitions}"
            
            assert final_entry.senses[0].definition == 'Original definition that should be preserved', \
                f"Definition property failed! Got: {final_entry.senses[0].definition}"
            
            print("✅ SUCCESS: Definition preserved in web form simulation!")

    @pytest.mark.integration
    def test_web_form_with_new_definition(self, app):
        """
        Test adding a new definition through web form (user's exact scenario).
        """
        with app.app_context():
            
            # 1. Original entry (empty or minimal)
            original_entry_data = {
                'id': 'test_web_entry_new',
                'lexical_unit': {'en': 'newword'},
                'senses': [
                    {
                        'id': 'sense1',
                        # No definition initially, or empty definition
                        'grammatical_info': 'noun'
                    }
                ]
            }
            
            # 2. User adds a definition and submits form
            form_submission_with_new_definition = {
                'id': 'test_web_entry_new',
                'lexical_unit': {'en': 'newword'},
                'senses': [
                    {
                        'id': 'sense1',
                        'definition': {'en': 'New definition added by user'},  # User added this
                        'grammatical_info': 'noun'
                    }
                ]
            }
            
            print(f"Original definition: {original_entry_data['senses'][0].get('definition', 'NONE')}")
            print(f"Form data definition: {form_submission_with_new_definition['senses'][0].get('definition')}")
            
            # 3. Test the merging process
            merged_data = merge_form_data_with_entry_data(form_submission_with_new_definition, original_entry_data)
            
            # 4. Create entry from merged data
            final_entry = Entry(**merged_data)
            
            print(f"Final entry definition: {final_entry.senses[0].definitions}")
            print(f"Final entry definition property: {final_entry.senses[0].definition}")
            
            # 5. CRITICAL TEST: New definition should be saved
            assert final_entry.senses[0].definitions == {'en': 'New definition added by user'}, \
                f"New definition was not saved! Got: {final_entry.senses[0].definitions}"
            
            assert final_entry.senses[0].definition == 'New definition added by user', \
                f"New definition property failed! Got: {final_entry.senses[0].definition}"
            
            print("✅ SUCCESS: New definition saved through web form simulation!")


if __name__ == '__main__':
    pytest.main([__file__, '-v', '-s'])
