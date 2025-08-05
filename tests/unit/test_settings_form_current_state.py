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
        PROBLEM: Source language code is a text input, not a dropdown.
        
        Users have to manually type language codes instead of selecting
        from a list. This is part of the UX nightmare.
        """
        with app.app_context():
            form = SettingsForm()
            
            # Source language code field exists but is just a text input
            assert hasattr(form, 'source_language_code')
            assert form.source_language_code.type == 'StringField'
            
            # There's NO dropdown with language options
            # This is what we need to fix

    def test_current_form_has_no_target_language_selection_ui(self, app: Flask) -> None:
        """
        PROBLEM: Target languages have no proper selection interface.
        
        There's just a hidden JSON field and a checkbox list that doesn't
        show available languages. Users can't easily select multiple target languages.
        """
        with app.app_context():
            form = SettingsForm()
            
            # There's a hidden JSON field for storage
            assert hasattr(form, 'target_languages_json')
            assert form.target_languages_json.type == 'HiddenField'
            
            # There's a checkbox field but it has no choices populated
            assert hasattr(form, 'available_target_languages')
            choices = form.available_target_languages.choices
            
            # The choices are empty - this is the problem!
            assert choices == [], f"Expected empty choices, got {choices}"
            
            # This means users see an empty interface with no languages to select

    def test_current_form_provides_no_language_options(self, app: Flask) -> None:
        """
        PROBLEM: Form doesn't populate language options automatically.
        
        Users have to know language codes manually instead of being
        presented with common language options.
        """
        with app.app_context():
            form = SettingsForm()
            
            # Form should have predefined language options but doesn't
            # This is what makes it a "UX nightmare"
            
            # Source language has no predefined options
            assert not hasattr(form.source_language_code, 'choices')
            
            # Target languages have no predefined options
            assert form.available_target_languages.choices == []

    def test_form_population_from_config_works_for_basic_data(self, app: Flask) -> None:
        """
        CURRENT WORKING FEATURE: Form can be populated from config.
        
        This part works - we can load existing settings into the form.
        We need to preserve this functionality while fixing the UX.
        """
        # Create temporary config
        with tempfile.TemporaryDirectory() as temp_dir:
            config_manager = ConfigManager(temp_dir)
            
            # Create form and populate it
            with app.app_context():
                form = SettingsForm()
                form.populate_from_config(config_manager)
                
                # Basic population should work
                assert form.project_name.data is not None
                assert form.source_language_code.data is not None
                assert form.source_language_name.data is not None

    def test_form_can_save_to_config(self, app: Flask) -> None:
        """
        CURRENT WORKING FEATURE: Form can save data to config.
        
        This part works - we can save form data to configuration.
        We need to preserve this while fixing the UX.
        """
        with tempfile.TemporaryDirectory() as temp_dir:
            config_manager = ConfigManager(temp_dir)
            
            with app.app_context():
                form = SettingsForm()
                form.project_name.data = "Test Project"
                form.source_language_code.data = "en"
                form.source_language_name.data = "English"
                form.target_languages_json.data = json.dumps([
                    {"code": "es", "name": "Spanish"},
                    {"code": "fr", "name": "French"}
                ])
                
                # Convert to dict and save
                form_data = form.to_dict()
                config_manager.update_current_settings(form_data)
                
                # Should be able to retrieve saved data
                saved_project_name = config_manager.get_project_name()
                assert saved_project_name == "Test Project"


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
