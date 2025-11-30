"""
Unit tests for lexical_unit field serialization.

Tests that lexical_unit is properly serialized as a multilingual dictionary
from the form fields, not as a simple string.
"""
from __future__ import annotations
import pytest
from typing import Dict, Any


class TestLexicalUnitSerialization:
    """Test suite for lexical_unit serialization from form to JSON."""
    
    def test_lexical_unit_single_language_serialization(self):
        """Test that a single-language lexical_unit serializes correctly."""
        # Simulated form data from FormSerializer
        form_data = {
            'lexical_unit': {
                'en': {
                    'lang': 'en',
                    'text': 'test'
                }
            }
        }
        
        # The serialized data should have lexical_unit as a dict {lang: text}
        expected_lexical_unit = {'en': 'test'}
        
        # Extract lexical_unit properly
        actual = self._extract_lexical_unit(form_data['lexical_unit'])
        
        assert actual == expected_lexical_unit, \
            f"Expected {expected_lexical_unit}, got {actual}"
    
    def test_lexical_unit_multiple_languages_serialization(self):
        """Test that multi-language lexical_unit serializes correctly."""
        form_data = {
            'lexical_unit': {
                'en': {
                    'lang': 'en',
                    'text': 'dog'
                },
                'es': {
                    'lang': 'es',
                    'text': 'perro'
                },
                'fr': {
                    'lang': 'fr',
                    'text': 'chien'
                }
            }
        }
        
        expected_lexical_unit = {
            'en': 'dog',
            'es': 'perro',
            'fr': 'chien'
        }
        
        actual = self._extract_lexical_unit(form_data['lexical_unit'])
        
        assert actual == expected_lexical_unit, \
            f"Expected {expected_lexical_unit}, got {actual}"
    
    def test_lexical_unit_empty_text_filtered(self):
        """Test that empty lexical_unit texts are filtered out."""
        form_data = {
            'lexical_unit': {
                'en': {
                    'lang': 'en',
                    'text': 'test'
                },
                'es': {
                    'lang': 'es',
                    'text': ''  # Empty should be filtered
                }
            }
        }
        
        expected_lexical_unit = {'en': 'test'}
        
        actual = self._extract_lexical_unit(form_data['lexical_unit'])
        
        assert actual == expected_lexical_unit, \
            f"Expected {expected_lexical_unit}, got {actual}"
    
    def test_lexical_unit_requires_at_least_one_language(self):
        """Test that lexical_unit with no valid languages raises error."""
        form_data = {
            'lexical_unit': {}
        }
        
        with pytest.raises(ValueError, match="lexical_unit must have at least one language"):
            self._extract_lexical_unit(form_data['lexical_unit'])
    
    def test_lexical_unit_invalid_structure_raises_error(self):
        """Test that invalid lexical_unit structure raises proper error."""
        # Old-style string format should raise error
        invalid_form_data = {
            'lexical_unit': 'just_a_string'
        }
        
        with pytest.raises(ValueError, match="lexical_unit must be a dict"):
            self._extract_lexical_unit(invalid_form_data['lexical_unit'])
    
    def test_lexical_unit_missing_text_field_raises_error(self):
        """Test that lexical_unit without text field raises error."""
        form_data = {
            'lexical_unit': {
                'en': {
                    'lang': 'en'
                    # Missing 'text' field
                }
            }
        }
        
        with pytest.raises(ValueError, match="lexical_unit.en missing required 'text' field"):
            self._extract_lexical_unit(form_data['lexical_unit'])
    
    def _extract_lexical_unit(self, raw_data: Any) -> Dict[str, str]:
        """
        Extract and validate lexical_unit from form data.
        
        This mimics what the server-side processing should do.
        
        Args:
            raw_data: The raw lexical_unit data from form serialization
            
        Returns:
            Dict mapping language codes to headword text
            
        Raises:
            ValueError: If the structure is invalid
        """
        if not isinstance(raw_data, dict):
            raise ValueError(f"lexical_unit must be a dict, got {type(raw_data)}")
        
        result = {}
        
        for lang_code, lang_data in raw_data.items():
            if not isinstance(lang_data, dict):
                raise ValueError(
                    f"lexical_unit.{lang_code} must be a dict with 'lang' and 'text' fields"
                )
            
            if 'text' not in lang_data:
                raise ValueError(
                    f"lexical_unit.{lang_code} missing required 'text' field"
                )
            
            text = lang_data['text']
            
            # Filter out empty strings
            if text and isinstance(text, str) and text.strip():
                result[lang_code] = text.strip()
        
        if not result:
            raise ValueError("lexical_unit must have at least one language with non-empty text")
        
        return result


class TestLexicalUnitIntegrationWithEntry:
    """Test that lexical_unit integrates correctly with Entry model."""
    
    def test_entry_accepts_multilingual_lexical_unit(self):
        """Test that Entry model accepts the serialized lexical_unit format."""
        from app.models.entry import Entry
        
        # This is what should be sent to the Entry constructor after serialization
        entry_data = {
            'id': 'test_entry',
            'lexical_unit': {
                'en': 'test',
                'es': 'prueba'
            }
        }
        
        entry = Entry(**entry_data)
        
        assert entry.lexical_unit == {'en': 'test', 'es': 'prueba'}
        assert entry.get_lexical_unit('en') == 'test'
        assert entry.get_lexical_unit('es') == 'prueba'
    
    def test_entry_rejects_string_lexical_unit(self):
        """Test that Entry model rejects string lexical_unit (old format)."""
        from app.models.entry import Entry
        
        invalid_data = {
            'id': 'test_entry',
            'lexical_unit': 'just_a_string'  # Should be rejected
        }
        
        with pytest.raises(ValueError, match="lexical_unit must be a dict"):
            Entry(**invalid_data)
