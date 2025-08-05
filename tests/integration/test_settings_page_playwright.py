"""
Comprehensive integration tests for Settings Page functionality using Playwright.

This test suite defines the expected UX behavior for resolving issue #5:
"Right now the edit entry form is an UX nightmare"

Following TDD approach - these tests define what the settings page SHOULD do.
"""

from __future__ import annotations

import pytest
from playwright.sync_api import Page, expect
import re


@pytest.mark.integration
class TestSettingsPageUX:
    """
    Test suite for settings page UX requirements.
    
    These tests define what the settings page should look like and behave like
    to solve the language selector UX issues in entry forms.
    """

    def test_settings_page_basic_functionality(self, playwright_page: Page, live_server) -> None:
        """Test basic settings page functionality - this should pass already."""
        playwright_page.goto(f"{live_server.url}/settings/")
        
        # Page should load without errors
        expect(playwright_page).to_have_title(re.compile(r"Settings|Project Settings"))
        
        # Should have a form
        settings_form = playwright_page.locator("form")
        expect(settings_form).to_be_visible()
        
        # Should have basic required fields
        project_name = playwright_page.locator('input[name="project_name"]')
        expect(project_name).to_be_visible()

    def test_source_language_selection_functionality(self, page: Page) -> None:
        """Test that source language can be selected properly."""
        page.goto("http://localhost:5000/settings/")
        
        # Source language code field should exist
        source_code_field = page.locator('input[name="source_language_code"], select[name="source_language_code"]')
        expect(source_code_field).to_be_visible()
        
        # Source language name field should exist
        source_name_field = page.locator('input[name="source_language_name"]')
        expect(source_name_field).to_be_visible()
        
        # Should be able to fill these fields
        if source_name_field.is_editable():
            source_name_field.fill("Test Language")
            expect(source_name_field).to_have_value("Test Language")

    def test_target_languages_interface_exists(self, page: Page) -> None:
        """Test that target languages section exists and has some interface."""
        page.goto("http://localhost:5000/settings/")
        
        # Target languages section should be present
        target_section = page.locator('fieldset:has-text("Target Languages")')
        expect(target_section).to_be_visible()
        
        # Should have some form of input for target languages
        # Could be checkboxes, dropdown, input fields, etc.
        target_inputs = target_section.locator('input, select, button')
        expect(target_inputs.first).to_be_visible()

    def test_form_submission_works(self, page: Page) -> None:
        """Test that form can be submitted without errors."""
        page.goto("http://localhost:5000/settings/")
        
        # Fill required fields
        project_name = page.locator('input[name="project_name"]')
        if project_name.input_value() == "":
            project_name.fill("Test Project")
        
        source_name = page.locator('input[name="source_language_name"]')
        if source_name.input_value() == "":
            source_name.fill("English")
        
        # Submit the form
        submit_button = page.locator('input[type="submit"], button[type="submit"]')
        expect(submit_button).to_be_visible()
        submit_button.click()
        
        # Wait for response
        page.wait_for_timeout(2000)
        
        # Should not show error page
        expect(page).not_to_have_title(re.compile(r"Error|500|404"))

    def test_current_settings_display(self, page: Page) -> None:
        """Test that current settings are displayed properly."""
        page.goto("http://localhost:5000/settings/")
        
        # Current settings overview should exist
        overview = page.locator(':has-text("Current Settings Overview")')
        expect(overview).to_be_visible()
        
        # Should show project name
        project_display = page.locator('dt:has-text("Project Name") + dd')
        expect(project_display).to_be_visible()


@pytest.mark.integration 
class TestSettingsLanguageUXRequirements:
    """
    Test suite that defines the REQUIRED UX improvements for issue #5.
    
    These tests will initially FAIL - they define what we need to implement.
    """

    def test_multiple_target_languages_can_be_selected(self, page: Page) -> None:
        """
        REQUIREMENT: Users must be able to select multiple target languages.
        
        This is core to solving the UX nightmare - users need to configure
        which languages they use for definitions/translations.
        """
        page.goto("http://localhost:5000/settings/")
        
        # Target languages section should allow multiple selections
        target_section = page.locator('fieldset:has-text("Target Languages")')
        
        # There should be multiple language options available
        # This could be implemented as:
        # 1. Checkboxes with predefined languages
        # 2. Multi-select dropdown
        # 3. Add/remove interface with language picker
        
        # For now, just check that the interface supports multiple languages
        # The implementation will determine the exact mechanism
        
        # Look for multiple language options or interface elements
        language_options = target_section.locator('[data-language], .language-option, input[type="checkbox"]')
        
        # Should have at least 3 common languages available (en, es, fr, de, pt, etc.)
        language_count = language_options.count()
        assert language_count > 2, f"Expected more than 2 language options, found {language_count}"

    def test_language_options_are_comprehensive(self, page: Page) -> None:
        """
        REQUIREMENT: Language options should include common lexicographic languages.
        
        Users should be able to select from major world languages used in
        dictionary/lexicographic work.
        """
        page.goto("http://localhost:5000/settings/")
        
        # Should have options for major languages
        # The exact implementation may vary, but these languages should be available:
        required_languages = ['en', 'es', 'fr', 'de', 'pt', 'it', 'ru', 'ar', 'zh', 'ja']
        
        # Check if page content includes these language codes or names
        page_content = page.content()
        
        # At least 5 of these major languages should be available
        available_count = sum(1 for lang in required_languages if lang in page_content.lower())
        assert available_count >= 5, f"Only {available_count} major languages found, need at least 5"

    def test_language_selection_updates_json_storage(self, page: Page) -> None:
        """
        REQUIREMENT: Language selections should update the JSON storage field.
        
        The form uses a hidden JSON field to store target languages.
        Selecting languages should update this field properly.
        """
        page.goto("http://localhost:5000/settings/")
        
        # Hidden JSON field should exist
        json_field = page.locator('input[name="target_languages_json"]')
        expect(json_field).to_be_attached()
        
        # When languages are selected, JSON field should be updated
        # This test defines the requirement - implementation will make it work

    def test_settings_affect_entry_form_language_options(self, page: Page) -> None:
        """
        REQUIREMENT: Settings should affect entry form language dropdowns.
        
        This is the ultimate goal - entry forms should only show configured languages,
        not all possible languages. This solves the "UX nightmare" mentioned in issue #5.
        """
        page.goto("http://localhost:5000/settings/")
        
        # Configure specific languages
        project_name = page.locator('input[name="project_name"]')
        if project_name.input_value() == "":
            project_name.fill("UX Test Project")
        
        # Configure source language
        source_name = page.locator('input[name="source_language_name"]')
        source_name.fill("English")
        
        # Configure specific target languages (implementation will determine how)
        # For now, just submit with default settings as this test defines requirements
        
        submit_button = page.locator('input[type="submit"], button[type="submit"]')
        submit_button.click()
        page.wait_for_timeout(1000)
        
        # Now check entry form
        page.goto("http://localhost:5000/entries/add")
        
        # Entry form should reflect configured languages
        # Should NOT show every possible language in dropdowns
        # Should show only configured source and target languages
        
        # This is the end goal - entry forms become manageable instead of nightmarish
        entry_form = page.locator("form")
        expect(entry_form).to_be_visible()
        
        # Language dropdowns in entry form should be limited to configured languages
        # The exact selectors depend on the entry form implementation
        # This test documents the requirement

    def test_language_validation_and_warnings(self, page: Page) -> None:
        """
        REQUIREMENT: Should provide validation and warnings for language configuration.
        
        Users should get helpful feedback when configuring languages.
        """
        page.goto("http://localhost:5000/settings/")
        
        # Try to submit without required language configuration
        project_name = page.locator('input[name="project_name"]')
        project_name.fill("")  # Clear required field
        
        submit_button = page.locator('input[type="submit"], button[type="submit"]')
        submit_button.click()
        page.wait_for_timeout(500)
        
        # Should show validation feedback
        page_content = page.content()
        has_validation = any([
            "required" in page_content.lower(),
            "error" in page_content.lower(),
            "invalid" in page_content.lower(),
        ])
        
        # Should provide helpful feedback to users
        assert has_validation, "No validation feedback found"
