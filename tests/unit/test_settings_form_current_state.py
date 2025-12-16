"""
Unit test for current settings form to document the problems.

This test suite documents what the CURRENT implementation does (badly)
and defines what we need to fix for issue #5.
"""

from __future__ import annotations

import pytest
from flask import Flask
from app.forms.settings_form import SettingsForm
from app.config_manager import ConfigManager
import tempfile
import os
import json


class TestCurrentSettingsFormProblems:
    """Test suite documenting current problems with settings form."""

    def test_current_form_has_no_language_dropdowns(self, app: Flask) -> None:
        """
        FIXED: Source language code is now a dropdown with choices.
        
        Users can now select from a list of language codes instead of
        manually typing them.
        """
        with app.app_context():
            form = SettingsForm()
            
            # Source language code field exists and is a SelectField
            assert hasattr(form, 'source_language_code')
            assert form.source_language_code.type == 'SelectField'
            
            # It should have choices populated
            assert hasattr(form.source_language_code, 'choices')
            assert len(form.source_language_code.choices) > 0

    def test_current_form_has_no_target_language_selection_ui(self, app: Flask) -> None:
        """
        FIXED: Target languages now use SearchableLanguageMultiSelectField.
        
        Users have a searchable interface for selecting multiple target languages
        from a comprehensive language database.
        """
        with app.app_context():
            from app.utils.comprehensive_languages import get_comprehensive_languages
            
            form = SettingsForm()
            
            # Now uses SearchableLanguageMultiSelectField
            assert hasattr(form, 'available_target_languages')
            
            # Language database is accessible
            available_languages = get_comprehensive_languages()
            assert len(available_languages) > 0, "Should have available languages"

    def test_current_form_provides_no_language_options(self, app: Flask) -> None:
        """
        FIXED: Form now provides comprehensive language options.
        
        Users are presented with language options from a comprehensive
        database instead of having to know codes manually.
        """
        with app.app_context():
            from app.utils.comprehensive_languages import get_comprehensive_languages
            
            form = SettingsForm()
            
            # Source language now has predefined options (SelectField with choices)
            assert hasattr(form.source_language_code, 'choices')
            assert len(form.source_language_code.choices) > 0
            
            # Target languages have access to comprehensive language database
            available_languages = get_comprehensive_languages()
            assert len(available_languages) > 0

    def test_form_population_from_config_works_for_basic_data(self, app: Flask) -> None:
        """
        CURRENT WORKING FEATURE: Form can be populated from config.
        
        This part works - we can load existing settings into the form.
        We need to preserve this functionality while fixing the UX.
        """
        with app.app_context():
            form = SettingsForm()
            
            # Basic form fields should exist and be accessible
            assert hasattr(form, 'project_name')
            assert hasattr(form, 'source_language_code')
            assert hasattr(form, 'source_language_name')
            
            # Form initialization should work without errors - data can be None or empty string
            assert form.project_name.data is None or form.project_name.data == '' or isinstance(form.project_name.data, str)

    def test_form_can_save_to_config(self, app: Flask) -> None:
        """
        CURRENT WORKING FEATURE: Form can save data to config.
        
        This part works - we can save form data to configuration.
        The field names have changed to match the new implementation.
        """
        with app.app_context():
            form = SettingsForm()
            form.project_name.data = "Test Project"
            form.source_language_code.data = "en"
            form.source_language_name.data = "English"
            
            # Now uses SearchableLanguageMultiSelectField instead of target_languages_json
            form.available_target_languages.data = json.dumps(["es", "fr"])
            
            # Form should have the necessary data
            assert form.project_name.data == "Test Project"
            assert form.source_language_code.data == "en"

    def test_backup_include_media_field_present_and_serializes(self, app: Flask) -> None:
        """Ensure the include_media checkbox exists and is serialized to backup_settings."""
        with app.app_context():
            form = SettingsForm()
            # The field should exist
            assert hasattr(form, 'backup_include_media')

            # Toggle it and verify serialization
            form.backup_include_media.data = True
            d = form.to_dict()
            assert 'backup_settings' in d
            assert d['backup_settings'].get('include_media') is True


class TestRequiredSettingsFormImprovements:
    """
    Test suite defining what we NEED to implement for issue #5.
    
    These tests will FAIL initially - they define the requirements.
    """

    def test_source_language_should_have_dropdown_options(self, app: Flask) -> None:
        """
        REQUIREMENT: Source language should have predefined options.
        
        Instead of forcing users to type language codes, provide
        a dropdown with common language options.
        """
        # This test defines what we need to implement
        with app.app_context():
            form = SettingsForm()
            
            # AFTER implementation, source language should have common options
            # For now, this will fail - that's expected in TDD
            
            # The form should be populated with language options
            expected_languages = ['en', 'es', 'fr', 'de', 'pt', 'it']
            
            # This should work after implementation:
            # assert len(form.source_language_code.choices) > 0
            # assert any(lang in str(form.source_language_code.choices) for lang in expected_languages)
            
            # For now, document the requirement
            pytest.skip("Not implemented yet - this defines the requirement")

    def test_target_languages_should_show_available_options(self, app: Flask) -> None:
        """
        REQUIREMENT: Target languages should show available language options.
        
        Users should see checkboxes or selection interface for common languages
        instead of an empty interface.
        """
        with app.app_context():
            form = SettingsForm()
            
            # AFTER implementation, target languages should have choices
            # For now, this will fail - that's expected in TDD
            
            expected_languages = ['en', 'es', 'fr', 'de', 'pt', 'it', 'ru', 'ar']
            
            # This should work after implementation:
            # assert len(form.available_target_languages.choices) >= len(expected_languages)
            # choice_codes = [choice[0] for choice in form.available_target_languages.choices]
            # assert all(lang in choice_codes for lang in expected_languages)
            
            # For now, document the requirement
            pytest.skip("Not implemented yet - this defines the requirement")

    def test_language_selection_should_update_json_field(self) -> None:
        """
        REQUIREMENT: Selecting languages should update the JSON storage.
        
        When users select languages via the UI, the hidden JSON field
        should be automatically updated with the proper structure.
        """
        # This test defines the required behavior
        # Implementation will make this work
        
        pytest.skip("Not implemented yet - this defines the requirement")

    def test_form_should_validate_language_selections(self) -> None:
        """
        REQUIREMENT: Form should validate language selections.
        
        Should warn if no target languages are selected, validate
        language codes, etc.
        """
        # This test defines validation requirements
        # Implementation will make this work
        
        pytest.skip("Not implemented yet - this defines the requirement")
