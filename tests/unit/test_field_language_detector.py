"""
Unit tests for field language detector.
"""

import unittest
from unittest.mock import MagicMock

from app.services.field_language_detector import FieldLanguageDetector


class TestFieldLanguageDetector(unittest.TestCase):
    """Tests for FieldLanguageDetector."""

    def setUp(self):
        """Set up test fixtures."""
        self.detector = FieldLanguageDetector()

    def test_detect_lexical_unit(self):
        """Test detection for lexical unit field."""
        mock_project = MagicMock()
        mock_project.source_language = {'code': 'en', 'name': 'English'}

        lang_code = self.detector.detect(
            'lexical_unit',
            {'en': 'test'},
            mock_project
        )

        self.assertEqual(lang_code, 'en')

    def test_detect_pronunciations(self):
        """Test detection for IPA field."""
        lang_code = self.detector.detect(
            'pronunciations',
            {'seh-fonipa': 'tɛst'},
            None
        )

        self.assertEqual(lang_code, 'seh-fonipa')

    def test_detect_from_keys(self):
        """Test detection from dictionary keys."""
        lang_code = self.detector.detect(
            'definition',
            {'fr': 'test', 'de': 'test'},
            None
        )

        # Should return first valid key
        self.assertIn(lang_code, ['fr', 'de'])

    def test_detect_from_dict_entry(self):
        """Test detection from entry data."""
        entry_data = {
            'lexical_unit': {'en': 'test'},
            'senses': [
                {
                    'definition': {'fr': 'test'},
                    'gloss': {'de': 'test'}
                }
            ]
        }

        mock_project = MagicMock()
        mock_project.source_language = {'code': 'en', 'name': 'English'}

        result = self.detector.detect_from_dict(entry_data, mock_project)

        self.assertIn('lexical_unit', result)
        self.assertIn('senses.0.definition', result)
        self.assertIn('senses.0.gloss', result)

    def test_get_base_field(self):
        """Test extracting base field name."""
        self.assertEqual(
            self.detector._get_base_field('senses.0.definition'),
            'definition'
        )
        self.assertEqual(
            self.detector._get_base_field('senses[0].definition'),
            'definition'
        )
        self.assertEqual(
            self.detector._get_base_field('lexical_unit'),
            'lexical_unit'
        )

    def test_is_valid_lang_code(self):
        """Test language code validation."""
        valid_codes = ['en', 'en_US', 'fr-FR', 'seh-fonipa', 'zh-Hans']
        invalid_codes = ['', 'e', 'en_', 'en-US-US', '123']

        for code in valid_codes:
            self.assertTrue(
                self.detector._is_valid_lang_code(code),
                f"Expected {code} to be valid"
            )

        for code in invalid_codes:
            self.assertFalse(
                self.detector._is_valid_lang_code(code),
                f"Expected {code} to be invalid"
            )

    def test_normalize_lang_code(self):
        """Test language code normalization."""
        self.assertEqual(
            self.detector.normalize_lang_code('en-us'),
            'en-US'
        )
        self.assertEqual(
            self.detector.normalize_lang_code('en_us'),
            'en_US'
        )
        self.assertEqual(
            self.detector.normalize_lang_code('ipa'),
            'seh-fonipa'
        )
        self.assertEqual(
            self.detector.normalize_lang_code('x-ipa'),
            'seh-fonipa'
        )

    def test_get_languages_from_entry(self):
        """Test extracting languages from entry."""
        entry_data = {
            'lexical_unit': {'en': 'test', 'fr': 'test'},
            'senses': [
                {
                    'definition': {'de': 'test'},
                    'gloss': {'es': 'test'}
                }
            ]
        }

        languages = self.detector.get_languages_from_entry(entry_data)

        self.assertEqual(len(languages), 4)
        self.assertIn('en', languages)
        self.assertIn('fr', languages)
        self.assertIn('de', languages)
        self.assertIn('es', languages)

    def test_is_ipa_field(self):
        """Test IPA field detection."""
        self.assertTrue(self.detector.is_ipa_field('pronunciations'))
        self.assertTrue(self.detector.is_ipa_field('pronunciation'))
        self.assertTrue(self.detector.is_ipa_field('ipa'))
        self.assertFalse(self.detector.is_ipa_field('lexical_unit'))
        self.assertFalse(self.detector.is_ipa_field('definition'))

    def test_fallback_to_default(self):
        """Test fallback when no language detected."""
        mock_project = MagicMock()
        mock_project.source_language = {'code': 'en', 'name': 'English'}

        lang_code = self.detector.detect(
            'notes',
            {},  # Empty dict, no keys
            mock_project
        )

        # Should fall back to project source language
        self.assertEqual(lang_code, 'en')

    def test_inherit_from_parent(self):
        """Test language inheritance."""
        parent_lang = 'fr'

        lang_code = self.detector._resolve_language(
            source='inherit',
            field_value={},
            project_settings=None,
            parent_lang_code=parent_lang
        )

        self.assertEqual(lang_code, 'fr')


if __name__ == '__main__':
    unittest.main()
