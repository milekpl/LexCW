#!/usr/bin/env python3
"""
Unit tests for the improved settings form functionality.

These tests validate that our TDD implementation meets the requirements.
"""

from __future__ import annotations

import unittest
from unittest.mock import patch
from app import create_app
from app.forms.settings_form import SettingsForm
from app.utils.language_choices import get_source_language_choices, get_target_language_choices


class TestLanguageSelectionTDD(unittest.TestCase):
    """Test that our language selection meets TDD requirements."""

    def setUp(self) -> None:
        """Set up test client and app context."""
        self.app = create_app()
        self.app_context = self.app.app_context()
        self.app_context.push()

    def tearDown(self) -> None:
        """Clean up test context."""
        self.app_context.pop()

    def test_source_language_dropdown_requirements(self) -> None:
        """
        TDD REQUIREMENT: Source language should be a dropdown with predefined choices.
        
        This test validates that users can select from predefined source languages
        instead of typing language codes manually (solving UX nightmare).
        """
        with self.app.test_request_context():
            form = SettingsForm()
            
            # Should be a SelectField, not StringField
            self.assertEqual(form.source_language_code.__class__.__name__, 'SelectField')
            
            # Should have predefined choices
            choices = form.source_language_code.choices
            self.assertGreater(len(choices), 20, "Should have many language options")
            
            # Should include common languages
            choice_codes = [choice[0] for choice in choices]
            required_languages = ['en', 'es', 'fr', 'de', 'pt', 'it', 'ru', 'ar', 'zh', 'ja']
            for lang in required_languages:
                self.assertIn(lang, choice_codes, f"Should include {lang}")

    def test_multiple_target_language_selection_requirements(self) -> None:
        """
        TDD REQUIREMENT: Users must be able to select MULTIPLE target languages.
        
        This is the core requirement for solving issue #5 UX nightmare.
        """
        with self.app.test_request_context():
            form = SettingsForm()
            
            # Should be a SelectMultipleField (rendered as checkboxes)
            self.assertEqual(form.available_target_languages.__class__.__name__, 'SelectMultipleField')
            
            # Should support multiple selections
            choices = form.available_target_languages.choices
            self.assertGreater(len(choices), 20, "Should have many target language options")
            
            # Should be able to select multiple values
            form.available_target_languages.data = ['en', 'es', 'fr']
            self.assertEqual(len(form.available_target_languages.data), 3)

    def test_comprehensive_language_options_requirements(self) -> None:
        """
        TDD REQUIREMENT: Language options should be comprehensive for lexicographic work.
        
        Should include major world languages commonly used in dictionary projects.
        """
        source_choices = get_source_language_choices()
        target_choices = get_target_language_choices()
        
        # Should have substantial language coverage
        self.assertGreaterEqual(len(source_choices), 25, "Source languages should be comprehensive")
        self.assertGreaterEqual(len(target_choices), 25, "Target languages should be comprehensive")
        
        # Should have same language options for both
        source_codes = set(choice[0] for choice in source_choices)
        target_codes = set(choice[0] for choice in target_choices)
        self.assertEqual(source_codes, target_codes, "Source and target should have same languages")
        
        # Should include languages from different families
        required_languages = {
            'en': 'English',      # Germanic
            'es': 'Spanish',      # Romance
            'ar': 'Arabic',       # Semitic
            'zh': 'Chinese',      # Sino-Tibetan
            'hi': 'Hindi',        # Indo-Aryan
            'ja': 'Japanese',     # Japonic
            'sw': 'Swahili',      # Niger-Congo
            'ru': 'Russian',      # Slavic
        }
        
        for code, name in required_languages.items():
            self.assertIn(code, source_codes, f"Should include {name} ({code})")

    def test_form_to_dict_requirements(self) -> None:
        """
        TDD REQUIREMENT: Form should properly serialize to dictionary format.
        
        This enables proper storage and configuration management.
        """
        with self.app.test_request_context():
            form = SettingsForm()
            
            # Simulate form data
            form.project_name.data = 'Test Dictionary Project'
            form.source_language_code.data = 'en'
            form.source_language_name.data = 'English'
            form.available_target_languages.data = ['es', 'fr', 'de']
            
            result = form.to_dict()
            
            # Should have proper structure
            self.assertIn('project_name', result)
            self.assertIn('source_language', result)
            self.assertIn('target_languages', result)
            
            # Source language should be single object
            self.assertEqual(result['source_language']['code'], 'en')
            self.assertEqual(result['source_language']['name'], 'English')
            
            # Target languages should be list of objects
            self.assertIsInstance(result['target_languages'], list)
            self.assertEqual(len(result['target_languages']), 3)
            
            target_codes = [lang['code'] for lang in result['target_languages']]
            self.assertEqual(set(target_codes), {'es', 'fr', 'de'})

    def test_form_populate_from_config_requirements(self) -> None:
        """
        TDD REQUIREMENT: Form should properly load existing configuration.
        
        Users should see their current settings when the form loads.
        """
        with self.app.test_request_context():
            form = SettingsForm()
            
            # Test configuration data
            config_data = {
                'project_name': 'Existing Dictionary',
                'source_language': {'code': 'fr', 'name': 'French'},
                'target_languages': [
                    {'code': 'en', 'name': 'English'},
                    {'code': 'es', 'name': 'Spanish'},
                    {'code': 'de', 'name': 'German'}
                ]
            }
            
            form.populate_from_config(config_data)
            
            # Should populate all fields correctly
            self.assertEqual(form.project_name.data, 'Existing Dictionary')
            self.assertEqual(form.source_language_code.data, 'fr')
            self.assertEqual(form.source_language_name.data, 'French')
            
            # Target languages should be properly selected
            expected_target_codes = ['en', 'es', 'de']
            self.assertEqual(set(form.available_target_languages.data), set(expected_target_codes))

    def test_language_choices_consistency_requirements(self) -> None:
        """
        TDD REQUIREMENT: Language choices should be consistent across the application.
        
        The same language list should be used everywhere to avoid confusion.
        """
        # Language choices should come from centralized module
        source_choices = get_source_language_choices()
        target_choices = get_target_language_choices()
        
        # Should be tuples of (code, name)
        for choice in source_choices[:5]:
            self.assertIsInstance(choice, tuple)
            self.assertEqual(len(choice), 2)
            self.assertIsInstance(choice[0], str)  # code
            self.assertIsInstance(choice[1], str)  # name
        
        # Should include specific expected languages with correct names
        source_dict = dict(source_choices)
        self.assertEqual(source_dict['en'], 'English')
        self.assertEqual(source_dict['es'], 'Spanish')
        self.assertEqual(source_dict['fr'], 'French')
        self.assertEqual(source_dict['de'], 'German')


if __name__ == '__main__':
    unittest.main()
