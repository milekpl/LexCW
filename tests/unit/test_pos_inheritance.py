#!/usr/bin/env python3
"""
Unit tests for POS inheritance functionality in the entry form.

Tests verify that:
1. Entry-level POS field is auto-inherited when all senses agree
2. Entry-level POS field becomes required when there are discrepancies
3. UI correctly shows/hides required indicators
4. Validation works correctly for both scenarios
"""

import pytest
from app.models.entry import Entry


class TestPOSInheritance:
    """Test POS inheritance functionality."""

    def test_pos_inheritance_single_sense(self):
        """Test POS inheritance with a single sense."""
        # Create an entry with one sense
        sense_data = {
            'id': 'sense1',
            'definition': 'Test definition',
            'grammatical_info': 'Adjective'
        }
        
        entry = Entry(
            id_='test_entry',
            lexical_unit={'en': 'test'},
            senses=[sense_data]
        )
        
        # POS should be inherited
        assert entry.grammatical_info == 'Adjective'
    
    def test_pos_inheritance_multiple_senses_agree(self):
        """Test POS inheritance when multiple senses agree."""
        # Create an entry with multiple senses having the same POS
        sense_data = [
            {
                'id': 'sense1',
                'definition': 'First definition',
                'grammatical_info': 'Noun'
            },
            {
                'id': 'sense2',
                'definition': 'Second definition',
                'grammatical_info': 'Noun'
            }
        ]
        
        entry = Entry(
            id_='test_entry',
            lexical_unit={'en': 'test'},
            senses=sense_data
        )
        
        # POS should be inherited
        assert entry.grammatical_info == 'Noun'
    
    def test_pos_inheritance_multiple_senses_disagree(self):
        """Test POS behavior when multiple senses disagree."""
        # Create an entry with multiple senses having different POS
        sense_data = [
            {
                'id': 'sense1',
                'definition': 'First definition',
                'grammatical_info': 'Noun'
            },
            {
                'id': 'sense2',
                'definition': 'Second definition',
                'grammatical_info': 'Verb'
            }
        ]
        
        entry = Entry(
            id_='test_entry',
            lexical_unit={'en': 'test'},
            senses=sense_data
        )
        
        # POS should not be inherited (remains None since there's discrepancy)
        assert entry.grammatical_info is None
        
        # Validation should detect the discrepancy
        errors = []
        entry._validate_pos_consistency(errors)
        assert len(errors) > 0
        assert 'inconsistent' in errors[0].lower()
    
    def test_pos_inheritance_explicit_entry_level_pos(self):
        """Test that explicit entry-level POS is preserved."""
        # Create an entry with explicit POS that differs from senses
        sense_data = [
            {
                'id': 'sense1',
                'definition': 'Test definition',
                'grammatical_info': 'Adjective'
            }
        ]
        
        entry = Entry(
            id_='test_entry',
            lexical_unit={'en': 'test'},
            grammatical_info='Noun',  # Explicit POS
            senses=sense_data
        )
        
        # Explicit POS should be preserved
        assert entry.grammatical_info == 'Noun'
    
    def test_pos_inheritance_empty_senses(self):
        """Test POS behavior with no senses."""
        entry = Entry(
            id_='test_entry',
            lexical_unit={'en': 'test'},
            senses=[]
        )
        
        # No POS should be inherited
        assert entry.grammatical_info is None
    
    def test_pos_inheritance_senses_without_pos(self):
        """Test POS behavior when senses have no POS set."""
        # Create an entry with senses that have no POS
        sense_data = [
            {
                'id': 'sense1',
                'definition': 'Test definition'
                # No grammatical_info
            }
        ]
        
        entry = Entry(
            id_='test_entry',
            lexical_unit={'en': 'test'},
            senses=sense_data
        )
        
        # No POS should be inherited
        assert entry.grammatical_info is None
    
    def test_pos_inheritance_mixed_empty_and_set_senses(self):
        """Test POS behavior with mix of senses with and without POS."""
        # Create an entry with mixed senses
        sense_data = [
            {
                'id': 'sense1',
                'definition': 'First definition',
                'grammatical_info': 'Noun'
            },
            {
                'id': 'sense2',
                'definition': 'Second definition'
                # No grammatical_info
            }
        ]
        
        entry = Entry(
            id_='test_entry',
            lexical_unit={'en': 'test'},
            senses=sense_data
        )
        
        # Should inherit from the sense that has POS set
        assert entry.grammatical_info == 'Noun'
    
    def test_pos_validation_consistency_success(self):
        """Test POS validation when there's no discrepancy."""
        # Create an entry where entry and senses agree
        sense_data = [
            {
                'id': 'sense1',
                'definition': 'Test definition',
                'grammatical_info': 'Adjective'
            }
        ]
        
        entry = Entry(
            id_='test_entry',
            lexical_unit={'en': 'test'},
            grammatical_info='Adjective',
            senses=sense_data
        )
        
        # Validation should pass
        errors = []
        entry._validate_pos_consistency(errors)
        assert len(errors) == 0
    
    def test_pos_validation_consistency_failure(self):
        """Test POS validation when there's a discrepancy."""
        # Create an entry where entry and senses disagree
        sense_data = [
            {
                'id': 'sense1',
                'definition': 'Test definition',
                'grammatical_info': 'Adjective'
            }
        ]
        
        entry = Entry(
            id_='test_entry',
            lexical_unit={'en': 'test'},
            grammatical_info='Noun',  # Different from sense
            senses=sense_data
        )
        
        # Validation should fail
        errors = []
        entry._validate_pos_consistency(errors)
        assert len(errors) > 0
        assert 'does not match' in errors[0].lower()


if __name__ == '__main__':
    pytest.main([__file__])
