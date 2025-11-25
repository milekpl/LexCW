#!/usr/bin/env python3
"""
Critical test for data loss during form saving.

This test ensures that when an entry is saved without any changes,
NO data is lost (definitions, grammatical categories, etc.).
"""

import pytest
from app.models.entry import Entry
from app.utils.multilingual_form_processor import merge_form_data_with_entry_data


class TestDataLossOnSave:
    """Test to prevent data loss when saving entries."""

    def test_save_without_changes_preserves_all_data(self):
        """Critical test: Saving an entry without changes should preserve ALL data."""
        
        # Original entry data (what would be in the database)
        original_entry_data = {
            'id': 'Protestant_2',
            'lexical_unit': {'en': 'Protestant'},
            'homograph_number': 2,
            'grammatical_info': None,  # Entry has no POS
            'morph_type': 'stem',
            'senses': [
                {
                    'id': 'Protestant_2_s1',
                    'definition': {'en': {'text': 'A member of a Protestant church'}},  # CRITICAL: This should NOT be cleared
                    'grammatical_info': 'noun',  # CRITICAL: This should NOT be cleared
                    'gloss': {
                        'en': {'text': 'Protestant person'},
                        'fr': {'text': 'personne protestante'}
                    },
                    'examples': [
                        {
                            'id': 'ex1',
                            'content': {'en': 'He is a Protestant.'},
                            'translation': {'fr': 'Il est protestant.'}
                        }
                    ]
                }
            ],
            'pronunciations': {'ipa': '/ˈprɑtəstənt/', 'audio': 'protestant.mp3'},
            'notes': {
                'general': {'en': 'Religious term', 'fr': 'Terme religieux'},
                'usage': {'en': 'Formal usage'}
            },
            'etymologies': [
                {
                    'type': 'borrowing',
                    'source': 'Latin',
                    'form': {'lang': 'la', 'text': 'protestans'},
                    'gloss': {'lang': 'en', 'text': 'protesting'}
                }
            ]
        }
        
        # Create original entry to verify initial state
        original_entry = Entry(**original_entry_data)
        print(f"Original entry definition: {original_entry.senses[0].definition}")
        print(f"Original entry grammatical_info: {original_entry.senses[0].grammatical_info}")
        
        # Simulate form data that might come from a "save without changes" operation
        # This represents what the JavaScript might send back
        form_data_no_changes = {
            'id': 'Protestant_2',
            'lexical_unit': {'en': 'Protestant'},
            'homograph_number': 2,
            'grammatical_info': '',  # Empty because entry has no POS
            'morph_type': 'stem',
            'senses': [
                {
                    'id': 'Protestant_2_s1',
                    # CRITICAL ISSUE: What if the form data is missing these fields?
                    # 'definition': Missing - this could cause data loss!
                    # 'grammatical_info': Missing - this could cause data loss!
                    'gloss': {
                        'en': {'text': 'Protestant person'},
                        'fr': {'text': 'personne protestante'}
                    }
                }
            ],
            'pronunciations': {'ipa': '/ˈprɑtəstənt/', 'audio': 'protestant.mp3'},
            'notes': {
                'general': {'en': 'Religious term', 'fr': 'Terme religieux'},
                'usage': {'en': 'Formal usage'}
            }
        }
        
        # Merge form data with existing entry data
        merged_data = merge_form_data_with_entry_data(form_data_no_changes, original_entry_data)
        
        # Create entry from merged data
        saved_entry = Entry(**merged_data)
        
        print(f"Saved entry definition: {saved_entry.senses[0].definition}")
        print(f"Saved entry grammatical_info: {saved_entry.senses[0].grammatical_info}")
        
        # CRITICAL ASSERTIONS: NO DATA SHOULD BE LOST
        
        # Definition should be preserved (check underlying definitions dict)
        assert saved_entry.senses[0].definitions == {'en': {'text': 'A member of a Protestant church'}}, \
            f"CRITICAL DATA LOSS: Definition was cleared! Got: {saved_entry.senses[0].definitions}"
        
        # Alternative check: the property should also work (returns the dict)
        assert saved_entry.senses[0].definition == {'en': {'text': 'A member of a Protestant church'}}, \
            f"CRITICAL DATA LOSS: Definition property not working! Got: {saved_entry.senses[0].definition}"
        
        # Grammatical info should be preserved  
        assert saved_entry.senses[0].grammatical_info == 'noun', \
            f"CRITICAL DATA LOSS: Grammatical info was cleared! Got: {saved_entry.senses[0].grammatical_info}"
        
        # Examples should be preserved
        assert len(saved_entry.senses[0].examples) == 1, \
            f"CRITICAL DATA LOSS: Examples were lost! Got: {len(saved_entry.senses[0].examples)} examples"
        
        # Etymologies should be preserved
        assert len(saved_entry.etymologies) == 1, \
            f"CRITICAL DATA LOSS: Etymologies were lost! Got: {len(saved_entry.etymologies)} etymologies"
        
        # All other data should be preserved
        assert saved_entry.lexical_unit == original_entry.lexical_unit
        assert saved_entry.homograph_number == original_entry.homograph_number
        assert saved_entry.morph_type == original_entry.morph_type
        assert saved_entry.pronunciations == original_entry.pronunciations
        assert saved_entry.notes == original_entry.notes

    def test_minimal_form_data_preserves_complex_entry(self):
        """Test that minimal form data preserves complex entry structure."""
        
        # Complex existing entry
        complex_entry_data = {
            'id': 'complex_entry',
            'lexical_unit': {'en': 'run', 'fr': 'courir'},
            'grammatical_info': 'verb',
            'senses': [
                {
                    'id': 'run_s1',
                    'definition': {
                        'en': {'text': 'To move rapidly on foot'},
                        'fr': {'text': 'Se déplacer rapidement à pied'}
                    },
                    'grammatical_info': 'verb',
                    'semantic_domain': 'motion',
                    'subsense_type': 'primary',
                    'examples': [
                        {'id': 'ex1', 'content': {'en': 'I run every morning'}},
                        {'id': 'ex2', 'content': {'en': 'She runs fast'}}
                    ]
                },
                {
                    'id': 'run_s2',
                    'definition': {
                        'en': {'text': 'A period of running'},
                        'fr': {'text': 'Une période de course'}
                    },
                    'grammatical_info': 'noun',
                    'semantic_domain': 'activity',
                    'subsense_type': 'derived'
                }
            ],
            'relations': [
                {'type': 'synonym', 'ref': 'sprint', 'traits': {'description': 'fast running'}}
            ],
            'variant_relations': [
                {'type': 'spelling', 'ref': 'runne', 'traits': {'description': 'archaic spelling'}}
            ]
        }
        
        # Minimal form data (what might come from a simple edit)
        minimal_form_data = {
            'id': 'complex_entry',
            'lexical_unit': {'en': 'run', 'fr': 'courir'},
            'grammatical_info': 'verb',
            # Missing most complex fields!
            'senses': [
                {
                    'id': 'run_s1',
                    # Missing: definition, grammatical_info, semantic_domain, subsense_type, examples
                },
                {
                    'id': 'run_s2',
                    # Missing: definition, grammatical_info, semantic_domain, subsense_type
                }
            ]
            # Missing: relations, variant_relations
        }
        
        # Merge and create entry
        merged_data = merge_form_data_with_entry_data(minimal_form_data, complex_entry_data)
        saved_entry = Entry(**merged_data)
        
        # ALL complex data should be preserved
        assert saved_entry.senses[0].definitions == {'en': {'text': 'To move rapidly on foot'}, 'fr': {'text': 'Se déplacer rapidement à pied'}}
        assert saved_entry.senses[0].grammatical_info == 'verb'
        assert saved_entry.senses[0].semantic_domain == 'motion'
        assert saved_entry.senses[0].subsense_type == 'primary'
        assert len(saved_entry.senses[0].examples) == 2
        
        assert saved_entry.senses[1].definitions == {'en': {'text': 'A period of running'}, 'fr': {'text': 'Une période de course'}}
        assert saved_entry.senses[1].grammatical_info == 'noun'
        assert saved_entry.senses[1].semantic_domain == 'activity'
        assert saved_entry.senses[1].subsense_type == 'derived'
        
        assert len(saved_entry.relations) == 2  # 1 regular relation + 1 variant_relation
        assert len(saved_entry.variant_relations()) == 1


if __name__ == '__main__':
    pytest.main([__file__])
