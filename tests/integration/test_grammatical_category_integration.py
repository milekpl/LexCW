#!/usr/bin/env python3
"""
Integration test for the grammatical category clearing fix.

This test simulates a complete form submission flow to ensure that
sense grammatical_info is preserved when saving entries.
"""

import pytest
from app.models.entry import Entry
from app.utils.multilingual_form_processor import merge_form_data_with_entry_data



@pytest.mark.integration
class TestGrammaticalCategoryIntegration:
    """Integration test for the grammatical category preservation fix."""

    @pytest.mark.integration
    def test_protestant_scenario_integration(self):
        """Test the specific Protestant(2) scenario that was reported."""
        
        # Simulate the existing Protestant(2) entry from the database
        existing_protestant_data = {
            'id': 'Protestant_2',
            'lexical_unit': {'en': 'Protestant'},
            'homograph_number': 2,
            'grammatical_info': None,  # Entry has no POS
            'morph_type': 'stem',
            'senses': [
                {
                    'id': 'Protestant_2_s1',
                    'definition': {'en': 'A member of a Protestant church'},
                    'grammatical_info': 'noun',  # Sense HAS POS - this was being cleared
                    'glosses': [
                        {'lang': 'en', 'text': 'Protestant person'},
                        {'lang': 'fr', 'text': 'personne protestante'}
                    ]
                }
            ],
            'pronunciations': {'ipa': '/ˈprɑtəstənt/'},
            'notes': {'general': {'en': 'Religious term'}}
        }
        
        # Create the original entry to verify initial state
        original_entry = Entry(**existing_protestant_data)
        assert original_entry.senses[0].grammatical_info == 'noun'
        # Entry should inherit POS from sense
        assert original_entry.grammatical_info == 'noun'
        
        # Simulate form data that might be missing sense grammatical_info
        # This could happen if the JavaScript form serializer fails to include it
        incomplete_form_data = {
            'id': 'Protestant_2',
            'lexical_unit': {'en': 'Protestant'},
            'homograph_number': 2,
            'grammatical_info': '',  # User didn't set entry-level POS
            'morph_type': 'stem',
            'senses': [
                {
                    'id': 'Protestant_2_s1',
                    'definition': {'en': 'A member of a Protestant church'},
                    # MISSING: grammatical_info - this is the bug scenario
                    'glosses': [
                        {'lang': 'en', 'text': 'Protestant person'},
                        {'lang': 'fr', 'text': 'personne protestante'}
                    ]
                }
            ],
            'pronunciations': {'ipa': '/ˈprɑtəstənt/'},
            'notes': {'general': {'en': 'Religious term'}}
        }
        
        # Simulate the server-side form processing
        merged_data = merge_form_data_with_entry_data(incomplete_form_data, existing_protestant_data)
        
        # Create entry from merged data (what happens in views.py)
        saved_entry = Entry(**merged_data)
        
        # CRITICAL: The sense should preserve its original grammatical_info
        assert saved_entry.senses[0].grammatical_info == 'noun', \
            f"BUG: Sense grammatical_info was cleared! Got: {saved_entry.senses[0].grammatical_info}"
        
        # Entry should still inherit the POS correctly
        assert saved_entry.grammatical_info == 'noun', \
            f"Entry should inherit POS from sense, got: {saved_entry.grammatical_info}"
        
        # Other fields should be preserved/updated correctly
        assert saved_entry.id == 'Protestant_2'
        assert saved_entry.lexical_unit == {'en': 'Protestant'}
        assert saved_entry.homograph_number == 2
        assert saved_entry.morph_type == 'stem'

    @pytest.mark.integration
    def test_multiple_senses_partial_form_data(self):
        """Test scenario with multiple senses where form data is partially missing."""
        
        # Existing entry with multiple senses having different POS
        existing_data = {
            'id': 'test_multiple',
            'lexical_unit': {'en': 'run'},
            'grammatical_info': None,  # No entry-level POS
            'senses': [
                {
                    'id': 'run_s1',
                    'definition': {'en': 'To move quickly on foot'},
                    'grammatical_info': 'verb',  # Should be preserved
                },
                {
                    'id': 'run_s2', 
                    'definition': {'en': 'A period of running'},
                    'grammatical_info': 'noun',  # Should be preserved
                }
            ]
        }
        
        # Form data with incomplete sense info
        form_data = {
            'id': 'test_multiple',
            'lexical_unit': {'en': 'run'},
            'grammatical_info': '',
            'senses': [
                {
                    'id': 'run_s1',
                    'definition': {'en': 'To move quickly on foot'},
                    # Missing grammatical_info
                },
                {
                    'id': 'run_s2',
                    'definition': {'en': 'A period of running'}, 
                    'grammatical_info': '',  # Empty string
                }
            ]
        }
        
        # Process the form data
        merged_data = merge_form_data_with_entry_data(form_data, existing_data)
        entry = Entry(**merged_data)
        
        # Both senses should preserve their original POS
        assert entry.senses[0].grammatical_info == 'verb'
        assert entry.senses[1].grammatical_info == 'noun'
        
        # Entry should have no POS (inconsistent senses)
        assert entry.grammatical_info is None or entry.grammatical_info == ''


if __name__ == '__main__':
    pytest.main([__file__])
