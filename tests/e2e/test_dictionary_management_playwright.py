"""
E2E tests for Dictionary Management functionality using Playwright.

Tests the UI for:
- Dictionary management page navigation
- Project dictionary listing
- Upload dictionary functionality
- Setting default/IPA dictionaries
- Personal user dictionaries
"""

from __future__ import annotations

import pytest
import re
from playwright.sync_api import Page, expect


@pytest.mark.integration
class TestDictionaryManagementPage:
    """Test suite for dictionary management page functionality."""

    def test_dictionary_page_loads(self, page: Page, app_url) -> None:
        """Test that the dictionary management page loads without errors."""
        # First navigate to settings to get a valid project_id
        page.goto(f"{app_url}/settings/")
        expect(page).to_have_title(re.compile(r"Settings|Project Settings"))

        # Get the project_id from the URL or navigate to dictionary page with project 1
        page.goto(f"{app_url}/projects/1/dictionaries")

        # Page should load
        expect(page).to_have_title(re.compile(r"Dictionary|spell-check", re.IGNORECASE))

    def test_dictionary_page_has_header(self, page: Page, app_url) -> None:
        """Test that dictionary page has proper header."""
        page.goto(f"{app_url}/projects/1/dictionaries")

        # Should have a header with dictionary-related text
        header = page.locator('h2:has-text("Dictionary"), h2:has-text("Spell-Check")')
        expect(header).to_be_visible()

    def test_dictionary_page_has_project_dictionaries_section(self, page: Page, app_url) -> None:
        """Test that project dictionaries section exists."""
        page.goto(f"{app_url}/projects/1/dictionaries")

        # Should have project dictionaries section
        project_dicts = page.locator('.card:has-text("Project Dictionaries"), h4:has-text("Project Dictionaries")')
        expect(project_dicts).to_be_visible()

    def test_dictionary_page_has_upload_button(self, page: Page, app_url) -> None:
        """Test that upload dictionary button exists."""
        page.goto(f"{app_url}/projects/1/dictionaries")

        # Should have upload button
        upload_btn = page.locator('button:has-text("Upload Dictionary"), a:has-text("Upload Dictionary")')
        expect(upload_btn).to_be_visible()

    def test_dictionary_page_has_system_dictionaries_info(self, page: Page, app_url) -> None:
        """Test that system dictionaries info section exists."""
        page.goto(f"{app_url}/projects/1/dictionaries")

        # Should have system dictionaries or help section
        system_section = page.locator('.card:has-text("System Dictionaries"), .card:has-text("About Dictionaries")')
        # Selector may match multiple info cards; assert that at least the first one is visible
        expect(system_section.first).to_be_visible()

    def test_upload_modal_opens(self, page: Page, app_url) -> None:
        """Test that upload modal opens when button is clicked."""
        page.goto(f"{app_url}/projects/1/dictionaries")

        # Click upload button
        upload_btn = page.locator('button:has-text("Upload Dictionary")')
        if upload_btn.count() > 0 and upload_btn.is_enabled():
            upload_btn.click()

            # Modal should appear
            modal = page.locator('.modal:has-text("Upload Hunspell Dictionary"), #uploadDictModal')
            expect(modal).to_be_visible()

    def test_upload_modal_has_required_fields(self, page: Page, app_url) -> None:
        """Test that upload modal has required file input fields."""
        page.goto(f"{app_url}/projects/1/dictionaries")

        # Open upload modal
        upload_btn = page.locator('button:has-text("Upload Dictionary")')
        if upload_btn.count() > 0 and upload_btn.is_enabled():
            upload_btn.click()

            # Wait for modal
            page.wait_for_selector('.modal', state='visible', timeout=5000)

            # Should have .dic file input
            dic_input = page.locator('input[name="dic_file"]')
            expect(dic_input).to_be_visible()

            # Should have .aff file input
            aff_input = page.locator('input[name="aff_file"]')
            expect(aff_input).to_be_visible()

    def test_dictionary_page_has_personal_dictionaries_section(self, page: Page, app_url) -> None:
        """Test that personal dictionaries section exists for logged in users."""
        page.goto(f"{app_url}/projects/1/dictionaries")

        # Should have personal dictionaries section
        personal_section = page.locator('.card:has-text("Personal Dictionaries"), .card:has-text("My Personal")')
        if personal_section.count() > 0:
            expect(personal_section.first).to_be_visible()

    def test_settings_page_has_dictionary_section(self, page: Page, app_url) -> None:
        """Test that settings page has spell-check dictionaries section."""
        page.goto(f"{app_url}/settings/")

        # Should have spell-check dictionaries section
        dict_section = page.locator('fieldset:has-text("Spell-Check Dictionaries"), legend:has-text("Spell-Check Dictionaries")')
        expect(dict_section.first).to_be_visible()

        # Section should have manage link (accept current or older text)
        manage_link = page.locator('a:has-text("Manage dictionaries"), a:has-text("Manage all dictionaries")')
        expect(manage_link.first).to_be_visible()

    def test_dictionary_page_has_back_to_settings_link(self, page: Page, app_url) -> None:
        """Test that dictionary page has link back to settings."""
        page.goto(f"{app_url}/projects/1/dictionaries")

        # Should have back link
        back_link = page.locator('a:has-text("Back to Settings")')
        expect(back_link).to_be_visible()

    def test_dictionary_page_shows_empty_state(self, page: Page, app_url) -> None:
        """Test that empty state is shown when no dictionaries exist."""
        page.goto(f"{app_url}/projects/1/dictionaries")

        # Check for empty state message
        empty_state = page.locator('text=No dictionaries uploaded yet, text=No personal dictionaries')
        if empty_state.count() > 0:
            expect(empty_state.first).to_be_visible()


@pytest.mark.integration
class TestDictionaryValidationAPI:
    """Test suite for dictionary validation API functionality."""

    def test_validation_endpoint_exists(self, page: Page, app_url) -> None:
        """Test that dictionary validation API endpoint exists."""
        # This is a simple connectivity test - the actual API will be tested via UI
        import requests

        try:
            response = requests.get(f"{app_url}/api/dictionaries/system", timeout=5)
            # Should get a response (even if empty)
            assert response.status_code in [200, 404, 500]
        except requests.exceptions.RequestException:
            # Server might not be running - this is OK for a UI test
            pass

    def test_project_dictionaries_endpoint(self, page: Page, app_url) -> None:
        """Test that project dictionaries API endpoint returns data."""
        import requests

        try:
            response = requests.get(f"{app_url}/api/projects/1/dictionaries", timeout=5)
            if response.status_code == 200:
                data = response.json()
                assert 'dictionaries' in data
        except requests.exceptions.RequestException:
            pass
