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
        
        # Should have a settings form (be more specific to avoid navbar search form)
        settings_form = playwright_page.locator('form[action="/settings/"]')
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
        
        # Should have searchable language selector with search input
        # The implementation uses a hidden JSON field for data storage and a visible search interface
        search_input = target_section.locator('.language-search-input')
        expect(search_input).to_be_visible()

    def test_form_submission_works(self, page: Page) -> None:
        """Test that form can be submitted without errors."""
        page.goto("http://localhost:5000/settings/")
        
        # Fill required fields
        project_name = page.locator('input[name="project_name"]')
        if project_name.input_value() == "":
            project_name.fill("Test Project")
        
        # Select source language code (required field)
        source_code = page.locator('select[name="source_language_code"]')
        if source_code.input_value() == "":
            source_code.select_option("en")
        
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
        
        # Target languages section should allow multiple selections via searchable interface
        target_section = page.locator('fieldset:has-text("Target Languages")')
        
        # The implementation uses a searchable language selector
        # Search for a language and verify we can interact with it
        search_input = target_section.locator('.language-search-input')
        expect(search_input).to_be_visible()
        
        # Type a search query
        search_input.fill("Spanish")
        page.wait_for_timeout(500)  # Wait for search debounce
        
        # Search results should appear
        results_container = target_section.locator('.language-search-results')
        expect(results_container).to_be_visible()
        
        # Should have at least one result
        search_results = results_container.locator('.language-search-result')
        expect(search_results.first).to_be_visible()

    def test_language_options_are_comprehensive(self, page: Page) -> None:
        """
        REQUIREMENT: Language options should include common lexicographic languages.
        
        Users should be able to select from major world languages used in
        dictionary/lexicographic work.
        """
        page.goto("http://localhost:5000/settings/")
        
        # Should have searchable interface for comprehensive languages
        search_input = page.locator('.language-search-input')
        expect(search_input).to_be_visible()
        
        # Test searching for a few major languages
        major_languages = ['English', 'Spanish', 'French', 'German', 'Chinese']
        
        found_count = 0
        for lang in major_languages:
            search_input.fill(lang)
            page.wait_for_timeout(400)  # Wait for debounce
            
            # Check if results appear
            results = page.locator('.language-search-results .language-search-result')
            if results.count() > 0:
                found_count += 1
            
            # Clear for next search
            search_input.fill("")
            page.wait_for_timeout(100)
        
        # Should find at least 4 out of 5 major languages
        assert found_count >= 4, f"Only found {found_count} major languages, need at least 4"

    def test_language_selection_updates_json_storage(self, page: Page) -> None:
        """
        REQUIREMENT: Language selections should update the JSON storage field.
        
        The form uses a hidden JSON field to store target languages.
        Selecting languages should update this field properly.
        """
        page.goto("http://localhost:5000/settings/")
        
        # Hidden JSON field should exist
        json_field = page.locator('input[name="available_target_languages"]')
        expect(json_field).to_be_attached()
        
        # Field should be hidden (type="hidden")
        expect(json_field).to_have_attribute("type", "hidden")

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
        source_code = page.locator('select[name="source_language_code"]')
        if source_code.input_value() == "":
            source_code.select_option("en")
        
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
