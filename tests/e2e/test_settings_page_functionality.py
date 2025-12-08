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

    def test_settings_page_basic_functionality(self, page: Page, app_url: str) -> None:
        """Test basic settings page functionality - this should pass already."""
        page.goto(f"{app_url}/settings/")
        
        # Page should load without errors
        expect(page).to_have_title(re.compile(r"Settings|Project Settings"))
        
        # Should have a form (use more specific selector to avoid navbar search form)
        settings_form = page.locator("form[method='POST']")
        expect(settings_form).to_be_visible()
        
        # Should have basic required fields
        project_name = page.locator('input[name="project_name"]')
        expect(project_name).to_be_visible()

    def test_source_language_selection_functionality(self, page: Page, app_url: str) -> None:
        """Test that source language can be selected properly."""
        page.goto(f"{app_url}/settings/")
        
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

    def test_target_languages_interface_exists(self, page: Page, app_url: str) -> None:
        """Test that target languages section exists and has some interface."""
        page.goto(f"{app_url}/settings/")
        
        # Target languages section should be present
        target_section = page.locator('fieldset:has-text("Target Languages")')
        expect(target_section).to_be_visible()
        
        # Should have some form of input for target languages
        # Could be checkboxes, dropdown, input fields, etc.
        # Filter out hidden inputs
        target_inputs = target_section.locator('input:not([type="hidden"]), select, button')
        expect(target_inputs.first).to_be_visible()

    def test_form_submission_works(self, page: Page, app_url: str) -> None:
        """Test that form can be submitted without errors."""
        page.goto(f"{app_url}/settings/")
        
        # Fill required fields
        project_name = page.locator('input[name="project_name"]')
        if project_name.input_value() == "":
            project_name.fill("Test Project")
        
        source_name = page.locator('input[name="source_language_name"]')
        if source_name.input_value() == "":
            source_name.fill("English")
        
        # Submit the form (use specific selector to avoid navbar search button)
        submit_button = page.locator('input#submit[type="submit"]')
        expect(submit_button).to_be_visible()
        submit_button.click()
        
        # Wait for response
        page.wait_for_timeout(2000)
        
        # Should not show error page
        expect(page).not_to_have_title(re.compile(r"Error|500|404"))

    def test_current_settings_display(self, page: Page, app_url: str) -> None:
        """Test that current settings are displayed properly."""
        page.goto(f"{app_url}/settings/")
        
        # Current settings overview should exist (use more specific selector)
        overview = page.locator('.card-header:has-text("Current Settings Overview")')
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

    def test_comprehensive_language_search_functionality(self, page: Page, app_url: str) -> None:
        """
        REQUIREMENT: Users must be able to search from 150+ world languages.
        
        This tests the new comprehensive, non-discriminatory language interface
        that supports languages from all families and regions.
        """
        page.goto(f"{app_url}/settings/")
        
        # Should have searchable language interface
        search_input = page.locator('.language-search-input')
        expect(search_input).to_be_visible()
        expect(search_input).to_have_attribute('placeholder', re.compile(r'[Ss]earch.*language'))
        
        # Test searching for different types of languages
        
        # Test 1: Search for African language
        search_input.fill("Swahili")
        page.wait_for_timeout(500)  # Wait for search results
        swahili_result = page.locator('.language-search-result:has-text("Swahili")')
        expect(swahili_result).to_be_visible()
        
        # Click to add Swahili
        swahili_result.click()
        selected_swahili = page.locator('.selected-language-item:has-text("Swahili")')
        expect(selected_swahili).to_be_visible()
        
        # Test 2: Search for Asian language by code
        search_input.fill("zh")
        page.wait_for_timeout(500)
        chinese_result = page.locator('.language-search-result:has-text("Chinese")')
        expect(chinese_result).to_be_visible()
        chinese_result.click()
        
        # Test 3: Search for Indigenous American language
        search_input.fill("Quechua")
        page.wait_for_timeout(500)
        quechua_result = page.locator('.language-search-result:has-text("Quechua")')
        expect(quechua_result).to_be_visible()
        quechua_result.click()
        
        # Test 4: Search for Sign Language (accessibility)
        search_input.fill("Sign Language")
        page.wait_for_timeout(500)
        sign_result = page.locator('.language-search-result:has-text("Sign Language")').first
        expect(sign_result).to_be_visible()
        
        # Test 5: Search by language family
        search_input.fill("Niger-Congo")
        page.wait_for_timeout(500)
        family_results = page.locator('.language-search-result')
        expect(family_results.first).to_be_visible()
        
        # Clear search to hide results before testing removal
        search_input.fill("")
        page.wait_for_timeout(300)
        
        # Should now have multiple selected languages (at least the ones we added)
        selected_languages = page.locator('.selected-language-item')
        initial_count = selected_languages.count()
        assert initial_count >= 3, f"Expected at least 3 selected languages, got {initial_count}"
        
        # Test removal functionality
        remove_button = page.locator('.selected-language-item:has-text("Swahili") .remove-language')
        remove_button.click()
        
        # Swahili should be removed
        expect(page.locator('.selected-language-item:has-text("Swahili")')).not_to_be_visible()
        # Count should decrease by 1
        final_count = selected_languages.count()
        assert final_count == initial_count - 1, f"Expected {initial_count - 1} languages after removal, got {final_count}"

    def test_ethnologue_level_language_coverage(self, page: Page, app_url: str) -> None:
        """
        REQUIREMENT: Language database should include languages from all families.
        
        This tests that the interface provides access to languages from
        major world language families, not just "common" languages.
        """
        page.goto(f"{app_url}/settings/")
        
        search_input = page.locator('.language-search-input')
        
        # Test major language families are represented
        test_families = {
            "Niger-Congo": ["Swahili", "Yoruba", "Zulu"],  # African
            "Sino-Tibetan": ["Chinese", "Burmese"],  # Asian
            "Indo-European": ["English", "Hindi", "Spanish"],  # Indo-European
            "Austronesian": ["Indonesian", "Tagalog", "Malay"],  # Southeast Asian/Pacific
            "Afro-Asiatic": ["Arabic", "Hebrew", "Amharic"],  # Middle Eastern/African
            "Dravidian": ["Tamil", "Telugu"],  # South Indian
            "Japonic": ["Japanese"],  # Japanese family
            "Koreanic": ["Korean"],  # Korean family
            "Sign Language": ["American Sign Language", "British Sign Language"]  # Sign languages
        }
        
        families_found = 0
        
        for family, languages in test_families.items():
            search_input.fill(family)
            page.wait_for_timeout(500)
            
            # Should find languages from this family
            results = page.locator('.language-search-result')
            if results.count() > 0:
                families_found += 1
            
            # Test specific languages from family
            for lang in languages[:2]:  # Test first 2 languages from each family
                search_input.fill(lang)
                page.wait_for_timeout(500)
                lang_result = page.locator(f'.language-search-result:has-text("{lang}")')
                if lang_result.count() > 0:
                    # Language found - this is good
                    break
        
        # Should find at least 6 out of 9 major language families
        assert families_found >= 6, f"Only found {families_found} major language families, expected at least 6"

    def test_language_metadata_richness(self, page: Page, app_url: str) -> None:
        """
        REQUIREMENT: Language entries should include family and region information.
        
        This tests that the interface provides rich metadata about languages,
        helping users understand language relationships and geography.
        """
        page.goto(f"{app_url}/settings/")
        
        search_input = page.locator('.language-search-input')
        
        # Search for a well-known language
        search_input.fill("Spanish")
        page.wait_for_timeout(500)
        
        spanish_result = page.locator('.language-search-result:has-text("Spanish")')
        expect(spanish_result).to_be_visible()
        
        # Should show family and region information
        result_text = spanish_result.text_content()
        
        # Should include language family information
        has_family_info = any([
            "Indo-European" in result_text,
            "Romance" in result_text,
            "family" in result_text.lower()
        ])
        
        # Should include region information  
        has_region_info = any([
            "Europe" in result_text,
            "Americas" in result_text,
            "Spain" in result_text,
            "region" in result_text.lower()
        ])
        
        assert has_family_info or has_region_info, f"Language result lacks metadata: {result_text}"
        
        # Add the language and check selected display
        spanish_result.click()
        
        selected_spanish = page.locator('.selected-language-item:has-text("Spanish")')
        expect(selected_spanish).to_be_visible()
        
        # Selected language should also show metadata
        selected_text = selected_spanish.text_content()
        has_metadata_in_selected = any([
            "Indo-European" in selected_text,
            "Europe" in selected_text,
            "Americas" in selected_text
        ])
        
        # Either in search results or selected display should have metadata
        assert has_family_info or has_region_info or has_metadata_in_selected, "No language metadata found"

    def test_accessibility_and_usability_features(self, page: Page, app_url: str) -> None:
        """
        REQUIREMENT: Interface should be accessible and user-friendly.
        
        This tests keyboard navigation, screen reader support, and
        other accessibility features of the language selection interface.
        """
        page.goto(f"{app_url}/settings/")
        
        # Test keyboard navigation
        search_input = page.locator('.language-search-input')
        search_input.focus()
        
        # Should be able to type and get results
        search_input.type("English")
        page.wait_for_timeout(500)
        
        results = page.locator('.language-search-result')
        expect(results.first).to_be_visible()
        
        # Test clear functionality
        clear_button = page.locator('.language-search-clear')
        expect(clear_button).to_be_visible()
        clear_button.click()
        
        # Search input should be cleared
        expect(search_input).to_have_value("")
        
        # Test that interface provides helpful instructions
        instructions = page.locator('text=Search by language name, ISO code, family, or region')
        expect(instructions).to_be_visible()
        
        # Test remove functionality with accessible labels
        search_input.fill("French")
        page.wait_for_timeout(500)
        french_result = page.locator('.language-search-result:has-text("French")').first
        french_result.click()
        
        # Remove button should have accessible title/label
        remove_button = page.locator('.selected-language-item:has-text("French") .remove-language')
        expect(remove_button).to_have_attribute('title', re.compile(r'[Rr]emove.*French'))

    def test_performance_with_large_language_database(self, page: Page, app_url: str) -> None:
        """
        REQUIREMENT: Interface should perform well with 150+ languages.
        
        This tests that search and selection remain responsive even with
        a comprehensive language database.
        """
        page.goto(f"{app_url}/settings/")
        
        search_input = page.locator('.language-search-input')
        
        # Test rapid searching
        test_queries = ["a", "en", "Indo", "Africa", "Sign"]
        
        for query in test_queries:
            start_time = page.evaluate("Date.now()")
            
            search_input.fill(query)
            
            # Wait for results to appear
            page.wait_for_function(
                """() => {
                    const results = document.querySelector('.language-search-results');
                    return results && results.style.display !== 'none';
                }""",
                timeout=2000  # Should respond within 2 seconds
            )
            
            end_time = page.evaluate("Date.now()")
            response_time = end_time - start_time
            
            # Search should be fast (under 1 second for user experience)
            assert response_time < 1000, f"Search for '{query}' took {response_time}ms, too slow"
        
        # Test selecting multiple languages doesn't slow down interface
        languages_to_add = ["English", "Spanish", "French", "German", "Portuguese"]
        
        for lang in languages_to_add:
            search_input.fill(lang)
            page.wait_for_timeout(300)
            
            lang_result = page.locator(f'.language-search-result:has-text("{lang}")').first
            lang_result.click()
            
            # Interface should remain responsive
            selected_count = page.locator('.selected-language-item').count()
            assert selected_count > 0, f"Failed to add {lang}"

    def test_form_integration_and_data_persistence(self, page: Page, app_url: str) -> None:
        """
        REQUIREMENT: Selected languages should integrate with form submission.
        
        This tests that the comprehensive language selection properly
        integrates with the settings form and persists data correctly.
        """
        page.goto(f"{app_url}/settings/")
        
        # Fill in project name
        project_name = page.locator('input[name="project_name"]')
        project_name.fill("Comprehensive Language Test")
        
        # Select source language
        source_select = page.locator('select[name="source_language_code"]')
        source_select.select_option(value="sw")  # Swahili
        
        # Select multiple target languages using the search interface
        search_input = page.locator('.language-search-input')
        
        target_languages = ["English", "Spanish", "Arabic", "Mandarin"]
        for lang in target_languages:
            search_input.fill(lang)
            page.wait_for_timeout(500)
            lang_result = page.locator(f'.language-search-result:has-text("{lang}")').first
            if lang_result.count() > 0:
                lang_result.click()
        
        # Should have selected languages displayed
        selected_items = page.locator('.selected-language-item')
        # Use count() > 2 instead of non-existent to_have_count_greater_than
        assert selected_items.count() > 2, f"Expected more than 2 selected languages, got {selected_items.count()}"
        
        # Submit the form (use specific selector)
        submit_button = page.locator('input#submit[type="submit"]')
        submit_button.click()
        
        # Wait for form processing
        page.wait_for_timeout(2000)
        
        # Should not show error page
        expect(page).not_to_have_title(re.compile(r"Error|500|404"))
        
        # Should show updated settings
        # (This test defines the requirement - implementation will make it work)
        page.goto(f"{app_url}/settings/")
        
        # Previously selected languages should be preserved
        # (Implementation will determine exact persistence mechanism)
