#!/usr/bin/env python3
"""
Unit tests for server-side morphological type loading.

Tests verify that:
1. Existing LIFT morph-type values are preserved
2. Empty morph-type fields get auto-classified
3. Auto-classification logic works correctly
4. Template receives correct morph-type data
"""

import pytest
from app.models.entry import Entry



@pytest.mark.integration
class TestMorphTypeServerSide:
    """Test server-side morphological type handling."""

    @pytest.mark.integration
    def test_existing_morph_type_preserved(self):
        """Test that existing LIFT morph-type values are preserved."""
        entry = Entry(id_='test_entry',
            lexical_unit={'en': 'test'},
            morph_type='stem',  # Already set from LIFT
            senses=[{"id": "sense1", "definition": {"en": "test definition"}}])
        
        # Should preserve existing value
        assert entry.morph_type == 'stem'
    
    @pytest.mark.integration
    def test_auto_classify_phrase(self):
        """Test auto-classification of phrases."""
        entry = Entry(id_='test_entry',
            lexical_unit={'en': 'test phrase'},
            # No morph_type set - should auto-classify
            senses=[{"id": "sense1", "definition": {"en": "test definition"}}])
        
        # Should auto-classify as phrase
        assert entry.morph_type == 'phrase'
    
    @pytest.mark.integration
    def test_auto_classify_prefix(self):
        """Test auto-classification of prefixes."""
        entry = Entry(id_='test_entry',
            lexical_unit={'en': 'pre-'},
            # No morph_type set - should auto-classify
            senses=[{"id": "sense1", "definition": {"en": "test definition"}}])
        
        # Should auto-classify as prefix
        assert entry.morph_type == 'prefix'
    
    @pytest.mark.integration
    def test_auto_classify_suffix(self):
        """Test auto-classification of suffixes."""
        entry = Entry(id_='test_entry',
            lexical_unit={'en': '-ing'},
            # No morph_type set - should auto-classify
            senses=[{"id": "sense1", "definition": {"en": "test definition"}}])
        
        # Should auto-classify as suffix
        assert entry.morph_type == 'suffix'
    
    @pytest.mark.integration
    def test_auto_classify_infix(self):
        """Test auto-classification of infixes."""
        entry = Entry(id_='test_entry',
            lexical_unit={'en': '-um-'},
            # No morph_type set - should auto-classify
            senses=[{"id": "sense1", "definition": {"en": "test definition"}}])
        
        # Should auto-classify as infix
        assert entry.morph_type == 'infix'
    
    @pytest.mark.integration
    def test_auto_classify_default_stem(self):
        """Test auto-classification defaults to stem."""
        entry = Entry(id_='test_entry',
            lexical_unit={'en': 'test'},
            # No morph_type set - should auto-classify
            senses=[{"id": "sense1", "definition": {"en": "test definition"}}])
        
        # Should auto-classify as stem (default)
        assert entry.morph_type == 'stem'


if __name__ == '__main__':
    pytest.main([__file__])
