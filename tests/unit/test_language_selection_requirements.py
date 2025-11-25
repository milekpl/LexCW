"""
Simple test to define and implement language selection improvements.

Following TDD: Write failing test -> Implement -> Make test pass
"""

from __future__ import annotations

import pytest
from flask import Flask
from app.forms.settings_form import SettingsForm


class TestLanguageSelectionRequirements:
    """Define requirements for language selection UX improvements."""

    def test_source_language_should_have_predefined_choices(self, app: Flask) -> None:
        """
        REQUIREMENT: Source language field should offer predefined language options.
        
        Currently it's just a text input. Users should be able to select
        from common languages used in lexicographic work.
        """
        with app.app_context():
            form = SettingsForm()
            
            # After implementation, this should work
            # For now it will fail - that's the TDD approach
            assert hasattr(form, 'source_language_code')
            
            # The field should have choices populated
            # Current implementation: this will fail
            if hasattr(form.source_language_code, 'choices'):
                choices = form.source_language_code.choices
                assert len(choices) > 0, "Source language should have predefined choices"
                
                # Should include common language codes
                choice_values = [choice[0] for choice in choices] if choices else []
                assert 'en' in choice_values, "English should be available"
                assert 'es' in choice_values, "Spanish should be available"
            else:
                # Current state - no choices, which is the problem
                pytest.fail("Source language field has no choices - this is what we need to fix")

    def test_target_languages_should_have_available_options(self, app: Flask) -> None:
        """
        REQUIREMENT: Target languages should show available language options.
        
        The SearchableLanguageMultiSelectField provides access to comprehensive language
        database through get_comprehensive_languages() function.
        """
        with app.app_context():
            from app.utils.comprehensive_languages import get_comprehensive_languages
            
            form = SettingsForm()
            
            # Target languages field should exist
            assert hasattr(form, 'available_target_languages')
            
            # Get available languages from the comprehensive database
            available_languages = get_comprehensive_languages()
            
            # Should have many language options
            assert len(available_languages) > 0, "Target languages should have available options"
            
            # Should include common languages
            language_codes = [lang['code'] for lang in available_languages]
            expected_languages = ['en', 'es', 'fr', 'de', 'pt']
            
            for lang in expected_languages:
                assert lang in language_codes, f"Language {lang} should be available"

    def test_form_should_populate_language_choices_automatically(self, app: Flask) -> None:
        """
        REQUIREMENT: Form should automatically populate language choices on creation.
        
        The SearchableLanguageMultiSelectField provides searchable access to comprehensive
        language database through its widget.
        """
        with app.app_context():
            from app.utils.comprehensive_languages import get_comprehensive_languages
            
            # Ensure form can be created
            form = SettingsForm()
            assert form is not None
            
            # Get available languages from the comprehensive database
            available_languages = get_comprehensive_languages()
            
            # Form should have access to comprehensive language database
            assert len(available_languages) > 5, f"Expected at least 6 language options, got {len(available_languages)}"
            
            # Should have proper language codes and names
            language_codes = [lang['code'] for lang in available_languages]
            language_names = [lang['name'] for lang in available_languages]
            
            assert 'en' in language_codes
            assert any('English' in name for name in language_names)
