"""
Unit tests for Etymology enhancements (Day 45-46).

Tests LIFT 0.13 etymology features:
- Gloss field (already implemented, verify)
- Comment field (custom field)
- Custom fields support
"""

from __future__ import annotations

import pytest
from app.models.entry import Etymology


class TestEtymologyGloss:
    """Test etymology gloss field (already implemented)."""
    
    def test_etymology_with_gloss(self):
        """Etymology can have gloss field."""
        etym = Etymology(
            type='inheritance',
            source='Latin',
            form={'la': 'cattus'},
            gloss={'en': 'cat'}
        )
        
        assert etym.gloss == {'en': 'cat'}
        assert etym.form == {'la': 'cattus'}
    
    def test_etymology_gloss_to_dict(self):
        """Etymology gloss included in to_dict()."""
        etym = Etymology(
            type='inheritance',
            source='Latin',
            form={'la': 'cattus'},
            gloss={'en': 'cat'}
        )
        
        etym_dict = etym.to_dict()
        assert etym_dict['gloss'] == {'en': 'cat'}
        assert etym_dict['form'] == {'la': 'cattus'}


class TestEtymologyComment:
    """Test etymology comment field (custom field)."""
    
    def test_etymology_with_comment(self):
        """Etymology can have comment custom field."""
        etym = Etymology(
            type='inheritance',
            source='Latin',
            form={'la': 'cattus'},
            gloss={'en': 'cat'},
            comment={'en': 'Borrowed via Old French'}
        )
        
        assert etym.comment == {'en': 'Borrowed via Old French'}
    
    def test_etymology_without_comment_defaults_to_none(self):
        """Etymology without comment has comment=None."""
        etym = Etymology(
            type='inheritance',
            source='Latin',
            form={'la': 'cattus'},
            gloss={'en': 'cat'}
        )
        
        assert etym.comment is None
    
    def test_etymology_comment_to_dict(self):
        """Etymology comment included in to_dict()."""
        etym = Etymology(
            type='inheritance',
            source='Latin',
            form={'la': 'cattus'},
            gloss={'en': 'cat'},
            comment={'en': 'Borrowed via Old French'}
        )
        
        etym_dict = etym.to_dict()
        assert etym_dict['comment'] == {'en': 'Borrowed via Old French'}


class TestEtymologyCustomFields:
    """Test etymology custom fields support."""
    
    def test_etymology_with_custom_fields(self):
        """Etymology can have custom_fields dict."""
        etym = Etymology(
            type='inheritance',
            source='Latin',
            form={'la': 'cattus'},
            gloss={'en': 'cat'},
            custom_fields={
                'certainty': {'en': 'high'},
                'note': {'en': 'Well-documented'}
            }
        )
        
        assert etym.custom_fields == {
            'certainty': {'en': 'high'},
            'note': {'en': 'Well-documented'}
        }
    
    def test_etymology_without_custom_fields_defaults_to_empty_dict(self):
        """Etymology without custom_fields has empty dict."""
        etym = Etymology(
            type='inheritance',
            source='Latin',
            form={'la': 'cattus'},
            gloss={'en': 'cat'}
        )
        
        assert etym.custom_fields == {}
    
    def test_etymology_custom_fields_to_dict(self):
        """Etymology custom_fields included in to_dict()."""
        etym = Etymology(
            type='inheritance',
            source='Latin',
            form={'la': 'cattus'},
            gloss={'en': 'cat'},
            custom_fields={
                'certainty': {'en': 'high'}
            }
        )
        
        etym_dict = etym.to_dict()
        assert etym_dict['custom_fields'] == {'certainty': {'en': 'high'}}
    
    def test_etymology_comment_and_custom_fields_together(self):
        """Etymology can have both comment and custom_fields."""
        etym = Etymology(
            type='inheritance',
            source='Latin',
            form={'la': 'cattus'},
            gloss={'en': 'cat'},
            comment={'en': 'Borrowed via Old French'},
            custom_fields={
                'certainty': {'en': 'high'},
                'date': {'en': '13th century'}
            }
        )
        
        assert etym.comment == {'en': 'Borrowed via Old French'}
        assert etym.custom_fields == {
            'certainty': {'en': 'high'},
            'date': {'en': '13th century'}
        }
        
        etym_dict = etym.to_dict()
        assert etym_dict['comment'] == {'en': 'Borrowed via Old French'}
        assert etym_dict['custom_fields'] == {
            'certainty': {'en': 'high'},
            'date': {'en': '13th century'}
        }
