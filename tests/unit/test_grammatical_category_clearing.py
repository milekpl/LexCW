#!/usr/bin/env python3
"""
Test to reproduce the grammatical category clearing issue.

This test reproduces the issue where saving a form clears the sense's 
grammatical category due to incorrect POS inheritance logic.
"""

import pytest
from app.models.entry import Entry


class TestGrammaticalCategoryClearing:
    """Test cases for grammatical category clearing bug."""

    def test_entry_creation_preserves_sense_grammatical_info(self):
        """Test that creating an Entry from dict preserves sense grammatical_info."""
        # Create entry data similar to what would come from a form
        entry_data = {
            'id': 'Protestant_2',
            'lexical_unit': {'en': 'Protestant'},
            'homograph_number': 2,
            # Entry has NO grammatical_info (empty)
            'grammatical_info': None,
            'senses': [
                {
                    'id': 'sense1',
                    'definition': {'en': 'A member of a Protestant church'},
                    'grammatical_info': 'noun',  # Sense HAS grammatical_info
                    'glosses': [{'lang': 'en', 'text': 'Protestant person'}]
                }
            ]
        }
        
        # Create entry from dict (simulating form submission)
        entry = Entry(**entry_data)
        
        # The entry should NOT have inherited POS (since there's only one sense)
        # But even if it did, the sense's grammatical_info should be preserved
        assert len(entry.senses) == 1
        sense = entry.senses[0]
        
        # This should NOT be cleared - this is the bug we're testing
        assert sense.grammatical_info == 'noun', f"Sense grammatical_info was cleared! Got: {sense.grammatical_info}"
    
    def test_entry_creation_with_multiple_different_pos_senses(self):
        """Test entry creation with multiple senses having different POS."""
        entry_data = {
            'id': 'test_entry',
            'lexical_unit': {'en': 'test'},
            # Entry has NO grammatical_info
            'grammatical_info': None,
            'senses': [
                {
                    'id': 'sense1',
                    'definition': {'en': 'As a noun'},
                    'grammatical_info': 'noun'
                },
                {
                    'id': 'sense2', 
                    'definition': {'en': 'As a verb'},
                    'grammatical_info': 'verb'
                }
            ]
        }
        
        entry = Entry(**entry_data)
        
        # Entry should remain without POS (inconsistent senses)
        assert entry.grammatical_info is None or entry.grammatical_info == ''
        
        # Both senses should preserve their original POS
        assert entry.senses[0].grammatical_info == 'noun'
        assert entry.senses[1].grammatical_info == 'verb'
    
    def test_entry_creation_with_consistent_pos_senses(self):
        """Test entry creation with multiple senses having same POS."""
        entry_data = {
            'id': 'test_entry',
            'lexical_unit': {'en': 'test'},
            # Entry has NO grammatical_info
            'grammatical_info': None,
            'senses': [
                {
                    'id': 'sense1',
                    'definition': {'en': 'First meaning'},
                    'grammatical_info': 'noun'
                },
                {
                    'id': 'sense2',
                    'definition': {'en': 'Second meaning'},
                    'grammatical_info': 'noun'
                }
            ]
        }
        
        entry = Entry(**entry_data)
        
        # Entry should inherit POS from consistent senses
        assert entry.grammatical_info == 'noun'
        
        # Both senses should preserve their original POS
        assert entry.senses[0].grammatical_info == 'noun'
        assert entry.senses[1].grammatical_info == 'noun'


if __name__ == '__main__':
    pytest.main([__file__])
