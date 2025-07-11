#!/usr/bin/env python3
"""
Unit test for the grammatical category clearing fix.

This test ensures that sense grammatical_info is preserved when form data
is missing or has empty values for sense fields.
"""

import pytest
from app.models.entry import Entry
from app.utils.multilingual_form_processor import merge_form_data_with_entry_data


class TestGrammaticalCategoryClearingFix:
    """Test the fix for grammatical category clearing issue."""

    def test_preserve_sense_grammatical_info_when_missing_from_form(self):
        """Test that sense grammatical_info is preserved when missing from form data."""
        
        # Existing entry data (from database)
        existing_data = {
            'id': 'Protestant_2',
            'lexical_unit': {'en': 'Protestant'},
            'grammatical_info': None,
            'senses': [
                {
                    'id': 'Protestant_2_s1',
                    'definition': {'en': 'A member of a Protestant church'},
                    'grammatical_info': 'noun',  # This should be preserved
                    'glosses': [{'lang': 'en', 'text': 'Protestant person'}]
                }
            ]
        }
        
        # Form data missing sense grammatical_info (the bug scenario)
        form_data = {
            'id': 'Protestant_2',
            'lexical_unit': {'en': 'Protestant'},
            'grammatical_info': '',
            'senses': [
                {
                    'id': 'Protestant_2_s1',
                    'definition': {'en': 'A member of a Protestant church'},
                    # Missing grammatical_info key - should preserve original
                    'glosses': [{'lang': 'en', 'text': 'Protestant person'}]
                }
            ]
        }
        
        # Merge data
        merged_data = merge_form_data_with_entry_data(form_data, existing_data)
        
        # Create entry
        entry = Entry(**merged_data)
        
        # The sense should preserve its original grammatical_info
        assert entry.senses[0].grammatical_info == 'noun', \
            f"Expected sense grammatical_info to be 'noun', got {entry.senses[0].grammatical_info}"

    def test_preserve_sense_grammatical_info_when_empty_in_form(self):
        """Test that sense grammatical_info is preserved when empty in form data."""
        
        # Existing entry data
        existing_data = {
            'id': 'test_entry',
            'lexical_unit': {'en': 'test'},
            'grammatical_info': None,
            'senses': [
                {
                    'id': 'test_s1',
                    'definition': {'en': 'test'},
                    'grammatical_info': 'verb',  # Should be preserved
                }
            ]
        }
        
        # Form data with empty sense grammatical_info
        form_data = {
            'id': 'test_entry',
            'lexical_unit': {'en': 'test'},
            'grammatical_info': '',
            'senses': [
                {
                    'id': 'test_s1',
                    'definition': {'en': 'test'},
                    'grammatical_info': '',  # Empty - should preserve original
                }
            ]
        }
        
        # Merge data
        merged_data = merge_form_data_with_entry_data(form_data, existing_data)
        
        # Create entry
        entry = Entry(**merged_data)
        
        # The sense should preserve its original grammatical_info
        assert entry.senses[0].grammatical_info == 'verb', \
            f"Expected sense grammatical_info to be 'verb', got {entry.senses[0].grammatical_info}"

    def test_update_sense_grammatical_info_when_changed_in_form(self):
        """Test that sense grammatical_info is updated when explicitly changed in form."""
        
        # Existing entry data
        existing_data = {
            'id': 'test_entry',
            'lexical_unit': {'en': 'test'},
            'grammatical_info': None,
            'senses': [
                {
                    'id': 'test_s1',
                    'definition': {'en': 'test'},
                    'grammatical_info': 'noun',  # Original value
                }
            ]
        }
        
        # Form data with changed sense grammatical_info
        form_data = {
            'id': 'test_entry',
            'lexical_unit': {'en': 'test'},
            'grammatical_info': '',
            'senses': [
                {
                    'id': 'test_s1',
                    'definition': {'en': 'test'},
                    'grammatical_info': 'verb',  # Changed value
                }
            ]
        }
        
        # Merge data
        merged_data = merge_form_data_with_entry_data(form_data, existing_data)
        
        # Create entry
        entry = Entry(**merged_data)
        
        # The sense should have the new grammatical_info
        assert entry.senses[0].grammatical_info == 'verb', \
            f"Expected sense grammatical_info to be 'verb', got {entry.senses[0].grammatical_info}"


if __name__ == '__main__':
    pytest.main([__file__])
