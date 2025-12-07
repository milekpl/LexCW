"""
Unit tests for Day 47-48: Example Enhancements

Tests for:
- Example source attribute
- Example note field (multilingual)
- Example custom fields
"""

from __future__ import annotations

import pytest
from app.models.example import Example


class TestExampleSource:
    """Test Example source attribute."""
    
    def test_example_with_source(self):
        """Example can have source attribute."""
        example = Example(
            id_='ex1',
            form={'en': 'This is an example'},
            source='corpus-ref-123'
        )
        
        assert example.source == 'corpus-ref-123'
    
    def test_example_without_source(self):
        """Example source is optional."""
        example = Example(
            id_='ex1',
            form={'en': 'This is an example'}
        )
        
        assert example.source is None
    
    def test_example_source_in_dict(self):
        """Example source appears in to_dict output."""
        example = Example(
            id_='ex1',
            form={'en': 'This is an example'},
            source='corpus-ref-123'
        )
        
        result = example.to_dict()
        assert result['source'] == 'corpus-ref-123'


class TestExampleNote:
    """Test Example note field (multilingual)."""
    
    def test_example_with_note(self):
        """Example can have multilingual note."""
        example = Example(
            id_='ex1',
            form={'en': 'This is an example'},
            note={'en': 'This is a note', 'fr': 'Ceci est une note'}
        )
        
        assert example.note == {'en': 'This is a note', 'fr': 'Ceci est une note'}
    
    def test_example_without_note(self):
        """Example note is optional."""
        example = Example(
            id_='ex1',
            form={'en': 'This is an example'}
        )
        
        assert example.note is None
    
    def test_example_note_in_dict(self):
        """Example note appears in to_dict when present."""
        example = Example(
            id_='ex1',
            form={'en': 'This is an example'},
            note={'en': 'This is a note'}
        )
        
        result = example.to_dict()
        assert result['note'] == {'en': 'This is a note'}
    
    def test_example_note_not_in_dict_when_empty(self):
        """Example note doesn't appear in to_dict when None."""
        example = Example(
            id_='ex1',
            form={'en': 'This is an example'}
        )
        
        result = example.to_dict()
        assert 'note' not in result or result.get('note') is None


class TestExampleCustomFieldsCombined:
    """Test Example with multiple enhancements combined."""
    
    def test_example_with_all_enhancements(self):
        """Example can have source, note, and custom fields together."""
        example = Example(
            id_='ex1',
            form={'en': 'This is an example'},
            translations={'fr': 'Ceci est un exemple'},
            source='corpus-ref-123',
            note={'en': 'Editorial note'},
            custom_fields={'certainty': {'en': 'high'}}
        )
        
        assert example.source == 'corpus-ref-123'
        assert example.note == {'en': 'Editorial note'}
        assert example.custom_fields == {'certainty': {'en': 'high'}}
    
    def test_example_dict_with_all_enhancements(self):
        """to_dict includes all enhancement attributes."""
        example = Example(
            id_='ex1',
            form={'en': 'This is an example'},
            source='corpus-ref-123',
            note={'en': 'Editorial note'},
            custom_fields={'certainty': {'en': 'high'}}
        )
        
        result = example.to_dict()
        assert result['source'] == 'corpus-ref-123'
        assert result['note'] == {'en': 'Editorial note'}
        assert result['custom_fields'] == {'certainty': {'en': 'high'}}
