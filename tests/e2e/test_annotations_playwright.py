"""
End-to-end tests for LIFT 0.13 Annotations using Playwright.

Tests the full annotation workflow including:
- Adding entry-level annotations
- Removing entry-level annotations
- Adding sense-level annotations
- Removing sense-level annotations
- Adding language variants to annotation content
- Removing language variants from annotation content

Following TDD approach - these tests verify the complete annotation UX.
"""

from __future__ import annotations

import pytest
from playwright.sync_api import Page, expect, Locator
import re


def expand_collapsible(page: Page, section_locator: Locator) -> None:
    """Helper to expand Bootstrap collapsible sections."""
    toggle_btn = section_locator.locator('.toggle-content-btn')
    if toggle_btn.is_visible():
        toggle_btn.click()
        page.wait_for_timeout(500)  # Wait for animation


@pytest.mark.integration
class TestAnnotationsPlaywright:
    """
    E2E test suite for LIFT 0.13 Annotations functionality.
    
    These tests verify that annotations can be added, edited, and removed
    correctly at both entry and sense levels, with multi-language support.
    """

    @pytest.fixture(autouse=True)
    def setup_test_entry(self, page: Page, app_url: str) -> None:
        """Navigate to entry form before each test."""
        # Go to add new entry page
        page.goto(f"{app_url}/entries/add")
        
        # Fill minimum required fields
        lexical_unit = page.locator('input[name="lexical_unit"]').first
        if lexical_unit.is_visible():
            lexical_unit.fill("test-word")
        
        # Wait for page to be ready
        page.wait_for_load_state("networkidle")

    def test_add_entry_level_annotation(self, page: Page, app_url: str) -> None:
        """Test adding an annotation at entry level."""
        # Click the Add Annotation button for entry
        add_btn = page.locator('.annotations-section-entry .add-annotation-btn')
        expect(add_btn).to_be_visible()
        add_btn.click()
        
        # A new annotation item should appear
        annotation_item = page.locator('.annotations-section-entry .annotation-item').first
        expect(annotation_item).to_be_visible()
        
        # Should have required fields
        name_input = annotation_item.locator('input[name*="annotations"][name*=".name"]')
        expect(name_input).to_be_visible()
        
        # Should have optional fields
        value_input = annotation_item.locator('input[name*="annotations"][name*=".value"]')
        expect(value_input).to_be_visible()
        
        who_input = annotation_item.locator('input[name*="annotations"][name*=".who"]')
        expect(who_input).to_be_visible()
        
        when_input = annotation_item.locator('input[name*="annotations"][name*=".when"]')
        expect(when_input).to_be_visible()
        
        # WHEN field should be auto-populated and readonly
        expect(when_input).to_have_attribute('readonly', '')
        expect(when_input).not_to_have_value('')
        
        # Content section should exist
        content_section = annotation_item.locator('.annotation-content-section')
        expect(content_section).to_be_visible()
        
        # Expand the collapsible content section
        toggle_btn = content_section.locator('.toggle-content-btn')
        if toggle_btn.is_visible():
            toggle_btn.click()
            page.wait_for_timeout(500)  # Wait for animation
        
        # Now the English textarea should be visible
        english_textarea = content_section.locator('textarea[data-lang="en"]')
        expect(english_textarea).to_be_visible()

    def test_remove_entry_level_annotation(self, page: Page, app_url: str) -> None:
        """Test removing an annotation at entry level."""
        # Add an annotation first
        add_btn = page.locator('.annotations-section-entry .add-annotation-btn')
        add_btn.click()
        
        # Verify it was added
        annotation_item = page.locator('.annotations-section-entry .annotation-item').first
        expect(annotation_item).to_be_visible()
        
        # Click remove button
        remove_btn = annotation_item.locator('.remove-annotation-btn')
        expect(remove_btn).to_be_visible()
        
        # Handle confirmation dialog
        page.on('dialog', lambda dialog: dialog.accept())
        remove_btn.click()
        
        # Annotation should be removed
        expect(annotation_item).not_to_be_visible()

    def test_add_sense_level_annotation(self, page: Page, app_url: str, ensure_sense) -> None:
        """Test adding an annotation at sense level."""
        # Ensure there is a real sense present (fixture handles add if necessary)
        ensure_sense(page)

        sense_item = page.locator('.sense-item:not(#default-sense-template):not(.default-sense-template):visible').first
        expect(sense_item).to_be_visible()

        # Scroll to sense item to ensure it's in viewport
        sense_item.scroll_into_view_if_needed()

        # Click the Add Annotation button for sense
        add_btn = sense_item.locator('.add-annotation-btn').first
        expect(add_btn).to_be_visible()
        add_btn.click()
        
        # A new annotation item should appear within the sense
        annotation_item = sense_item.locator('.annotation-item').first
        expect(annotation_item).to_be_visible()
        
        # Should have required fields
        name_input = annotation_item.locator('input[name*="annotations"][name*=".name"]')
        expect(name_input).to_be_visible()
        
        # Should have optional fields
        value_input = annotation_item.locator('input[name*="annotations"][name*=".value"]')
        expect(value_input).to_be_visible()
        
        who_input = annotation_item.locator('input[name*="annotations"][name*=".who"]')
        expect(who_input).to_be_visible()
        
        when_input = annotation_item.locator('input[name*="annotations"][name*=".when"]')
        expect(when_input).to_be_visible()
        
        # WHEN field should be auto-populated and readonly
        expect(when_input).to_have_attribute('readonly', '')
        expect(when_input).not_to_have_value('')

    def test_remove_sense_level_annotation(self, page: Page, app_url: str, ensure_sense) -> None:
        """Test removing an annotation at sense level."""
        # Ensure there is a real sense present
        ensure_sense(page)

        sense_item = page.locator('.sense-item:not(#default-sense-template):not(.default-sense-template):visible').first
        expect(sense_item).to_be_visible()
        sense_item.scroll_into_view_if_needed()

        # Add an annotation first
        add_btn = sense_item.locator('.add-annotation-btn').first
        add_btn.click()

        # Verify it was added
        annotation_item = sense_item.locator('.annotation-item').first
        expect(annotation_item).to_be_visible()

        # Click remove button
        remove_btn = annotation_item.locator('.remove-annotation-btn')
        expect(remove_btn).to_be_visible()

        # Handle confirmation dialog
        page.on('dialog', lambda dialog: dialog.accept())
        remove_btn.click()

        # Annotation should be removed
        expect(annotation_item).not_to_be_visible()

    def test_add_language_to_annotation_content(self, page: Page, app_url: str) -> None:
        """Test adding a language variant to annotation content."""
        # Add an entry-level annotation
        add_btn = page.locator('.annotations-section-entry .add-annotation-btn')
        add_btn.click()
        
        annotation_item = page.locator('.annotations-section-entry .annotation-item').first
        expect(annotation_item).to_be_visible()
        
        # Expand the collapsible content section
        content_section = annotation_item.locator('.annotation-content-section')
        expand_collapsible(page, content_section)
        
        # Click Add Language button
        add_lang_btn = annotation_item.locator('.add-annotation-language-btn')
        expect(add_lang_btn).to_be_visible()
        
        # Handle prompt for language code
        page.on('dialog', lambda dialog: dialog.accept('es'))  # Add Spanish
        add_lang_btn.click()
        
        # Spanish textarea should appear
        spanish_textarea = annotation_item.locator('textarea[data-lang="es"]')
        expect(spanish_textarea).to_be_visible(timeout=2000)
        
        # Should have a remove button
        remove_lang_btn = spanish_textarea.locator('..').locator('.remove-annotation-language-btn')
        expect(remove_lang_btn).to_be_visible()

    def test_remove_language_from_annotation_content(self, page: Page, app_url: str) -> None:
        """Test removing a language variant from annotation content."""
        # Add an entry-level annotation
        add_btn = page.locator('.annotations-section-entry .add-annotation-btn')
        add_btn.click()
        
        annotation_item = page.locator('.annotations-section-entry .annotation-item').first
        expect(annotation_item).to_be_visible()
        
        # Expand the collapsible content section
        content_section = annotation_item.locator('.annotation-content-section')
        expand_collapsible(page, content_section)
        
        # Add a language
        add_lang_btn = annotation_item.locator('.add-annotation-language-btn')
        page.on('dialog', lambda dialog: dialog.accept('de'))  # Add German
        add_lang_btn.click()
        
        # German textarea should appear
        german_textarea = annotation_item.locator('textarea[data-lang="de"]')
        expect(german_textarea).to_be_visible(timeout=2000)
        
        # Click remove button for German
        german_form = german_textarea.locator('..')
        remove_btn = german_form.locator('.remove-annotation-language-btn')
        expect(remove_btn).to_be_visible()
        remove_btn.click()
        
        # German textarea should be removed
        expect(german_textarea).not_to_be_visible()
        
        # English should still be there (can't remove English)
        english_textarea = annotation_item.locator('textarea[data-lang="en"]')
        expect(english_textarea).to_be_visible()

    def test_annotation_content_is_editable(self, page: Page, app_url: str) -> None:
        """Test that annotation content fields are editable."""
        # Add an entry-level annotation
        add_btn = page.locator('.annotations-section-entry .add-annotation-btn')
        add_btn.click()
        
        annotation_item = page.locator('.annotations-section-entry .annotation-item').first
        expect(annotation_item).to_be_visible()
        
        # Expand the collapsible content section
        content_section = annotation_item.locator('.annotation-content-section')
        expand_collapsible(page, content_section)
        
        # English content textarea should be editable
        english_textarea = annotation_item.locator('textarea[data-lang="en"]')
        expect(english_textarea).to_be_visible()
        expect(english_textarea).to_be_editable()
        
        # Should be able to type in it
        test_content = "This is a test annotation content."
        english_textarea.fill(test_content)
        expect(english_textarea).to_have_value(test_content)

    def test_multiple_annotations_can_be_added(self, page: Page, app_url: str) -> None:
        """Test that multiple annotations can be added to the same entry."""
        add_btn = page.locator('.annotations-section-entry .add-annotation-btn')
        
        # Add first annotation
        add_btn.click()
        expect(page.locator('.annotations-section-entry .annotation-item')).to_have_count(1)
        
        # Add second annotation
        add_btn.click()
        expect(page.locator('.annotations-section-entry .annotation-item')).to_have_count(2)
        
        # Add third annotation
        add_btn.click()
        expect(page.locator('.annotations-section-entry .annotation-item')).to_have_count(3)
        
        # Each should have unique indices
        annotations = page.locator('.annotations-section-entry .annotation-item').all()
        assert len(annotations) == 3

    def test_annotation_fields_persist_on_form(self, page: Page, app_url: str) -> None:
        """Test that annotation data persists in form fields."""
        # Add an entry-level annotation
        add_btn = page.locator('.annotations-section-entry .add-annotation-btn')
        add_btn.click()
        
        annotation_item = page.locator('.annotations-section-entry .annotation-item').first
        expect(annotation_item).to_be_visible()
        
        # Fill in annotation fields
        name_input = annotation_item.locator('input[name*=".name"]')
        name_input.fill('review-status')
        
        value_input = annotation_item.locator('input[name*=".value"]')
        value_input.fill('approved')
        
        who_input = annotation_item.locator('input[name*=".who"]')
        who_input.fill('editor-john')
        
        # Expand collapsible to access content textarea
        content_section = annotation_item.locator('.annotation-content-section')
        expand_collapsible(page, content_section)
        
        content_textarea = annotation_item.locator('textarea[data-lang="en"]')
        content_textarea.fill('This entry has been reviewed and approved.')
        
        # Verify all fields retain their values
        expect(name_input).to_have_value('review-status')
        expect(value_input).to_have_value('approved')
        expect(who_input).to_have_value('editor-john')
        expect(content_textarea).to_have_value('This entry has been reviewed and approved.')

    def test_duplicate_language_codes_are_prevented(self, page: Page, app_url: str) -> None:
        """Test that duplicate language codes are prevented."""
        # Add an entry-level annotation
        add_btn = page.locator('.annotations-section-entry .add-annotation-btn')
        add_btn.click()
        
        annotation_item = page.locator('.annotations-section-entry .annotation-item').first
        expect(annotation_item).to_be_visible()
        
        # Expand the collapsible content section
        content_section = annotation_item.locator('.annotation-content-section')
        expand_collapsible(page, content_section)
        
        # Try to add English (which already exists)
        add_lang_btn = annotation_item.locator('.add-annotation-language-btn')
        
        # Handle alert that should appear
        dialog_handled = False
        def handle_dialog(dialog):
            nonlocal dialog_handled
            # Should get an alert about duplicate language
            assert 'already exists' in dialog.message.lower() or 'duplicate' in dialog.message.lower()
            dialog.accept()
            dialog_handled = True
        
        page.on('dialog', handle_dialog)
        
        # First prompt will ask for language code
        page.evaluate("""
            window.prompt = function(message) {
                return 'en';  // Try to add English
            };
        """)
        
        add_lang_btn.click()
        
        # Should still only have one English textarea
        english_textareas = annotation_item.locator('textarea[data-lang="en"]')
        expect(english_textareas).to_have_count(1)

    def test_annotation_timestamp_format(self, page: Page, app_url: str) -> None:
        """Test that annotation timestamp is in correct format."""
        # Add an entry-level annotation
        add_btn = page.locator('.annotations-section-entry .add-annotation-btn')
        add_btn.click()
        
        annotation_item = page.locator('.annotations-section-entry .annotation-item').first
        when_input = annotation_item.locator('input[name*=".when"]')
        
        # Should match ISO datetime format (YYYY-MM-DDTHH:MM)
        timestamp_value = when_input.input_value()
        assert re.match(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}', timestamp_value), \
            f"Timestamp '{timestamp_value}' doesn't match ISO format YYYY-MM-DDTHH:MM"
