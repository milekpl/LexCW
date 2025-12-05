"""
End-to-end tests for LIFT 0.13 Custom Fields (Day 28) using Playwright.

Tests the full custom fields workflow including:
- Literal Meaning (entry-level)
- Exemplar (sense-level)
- Scientific Name (sense-level)
- Adding/removing language variants
- Field visibility and editability

Following TDD approach - these tests verify the complete custom fields UX.
"""

from __future__ import annotations

import pytest
from playwright.sync_api import Page, expect
import re


@pytest.mark.integration
class TestCustomFieldsPlaywright:
    """
    E2E test suite for LIFT 0.13 Custom Fields functionality.
    
    These tests verify that custom fields (literal-meaning, exemplar, scientific-name)
    can be added, edited, and removed correctly with multi-language support.
    """

    def _setup_test_entry(self, page: Page, live_server) -> None:
        """Navigate to entry form and add a sense (helper method, not a fixture)."""
        # Go to add new entry page
        page.goto(f"{live_server.url}/entries/add")
        
        # Wait for page to be ready
        page.wait_for_load_state("networkidle")
        
        # Fill minimum required fields for entry
        # Fill lexical unit in English
        lexical_unit_lang = page.locator('select[name="lexical_unit.en.lang"]').first
        if lexical_unit_lang.is_visible():
            lexical_unit_lang.select_option("en")
        
        lexical_unit_text = page.locator('input[name="lexical_unit.en.text"]').first
        if lexical_unit_text.is_visible():
            lexical_unit_text.fill("test-word")
        
        # Add a sense if not present
        add_sense_btn = page.locator('#add-sense-btn')
        if add_sense_btn.is_visible():
            add_sense_btn.click()
            page.wait_for_timeout(500)  # Wait for sense to be added
        
        # Fill sense definition
        sense_def = page.locator('textarea[name*="senses[0].definition"][name*=".text"]').first
        if sense_def.is_visible():
            sense_def.fill("test definition")

    def test_literal_meaning_field_visible(self, playwright_page: Page, live_server) -> None:
        """Test that literal meaning field is visible at entry level."""
        page = playwright_page
        self._setup_test_entry(page, live_server)
        
        # Literal meaning section should be visible
        literal_meaning_section = page.locator('.card').filter(has_text=re.compile(r'Literal Meaning', re.IGNORECASE))
        expect(literal_meaning_section).to_be_visible()
        
        # Should have an Add Language button
        add_lang_btn = literal_meaning_section.locator('.add-literal-meaning-language-btn')
        expect(add_lang_btn).to_be_visible()
        expect(add_lang_btn).to_contain_text('Add Language')

    def test_add_literal_meaning_language(self, page: Page) -> None:
        """Test adding a language to literal meaning field."""
        # Find literal meaning section
        literal_meaning_section = page.locator('.card').filter(has_text=re.compile(r'Literal Meaning', re.IGNORECASE))
        
        # Click Add Language button
        add_lang_btn = literal_meaning_section.locator('.add-literal-meaning-language-btn')
        add_lang_btn.click()
        
        # Wait for form to appear
        page.wait_for_timeout(500)
        
        # A new language form group should appear
        lang_form = literal_meaning_section.locator('.language-form-group').first
        expect(lang_form).to_be_visible()
        
        # Should have language selector
        lang_select = lang_form.locator('select.language-selector')
        expect(lang_select).to_be_visible()
        
        # Should have textarea for text
        text_area = lang_form.locator('textarea')
        expect(text_area).to_be_visible()
        
        # Should have remove button (use more general selector)
        remove_btn = lang_form.locator('.remove-literal-meaning-language-btn')
        expect(remove_btn).to_be_visible()

    def test_remove_literal_meaning_language(self, page: Page) -> None:
        """Test removing a language from literal meaning field."""
        # Find literal meaning section
        literal_meaning_section = page.locator('.card').filter(has_text=re.compile(r'Literal Meaning', re.IGNORECASE))
        
        # Add a language first
        add_lang_btn = literal_meaning_section.locator('.add-literal-meaning-language-btn')
        add_lang_btn.click()
        
        # Verify it was added
        lang_form = literal_meaning_section.locator('.language-form-group').first
        expect(lang_form).to_be_visible()
        
        # Click remove button
        remove_btn = lang_form.locator('button.remove-literal-meaning-language-btn')
        expect(remove_btn).to_be_visible()
        
        # Handle confirmation dialog
        page.on('dialog', lambda dialog: dialog.accept())
        remove_btn.click()
        
        # Wait a bit for removal
        page.wait_for_timeout(500)
        
        # Language form should be removed - check count instead of element visibility
        expect(literal_meaning_section.locator('.language-form-group')).to_have_count(0)

    def test_fill_literal_meaning_content(self, page: Page) -> None:
        """Test filling literal meaning with actual content."""
        # Find literal meaning section
        literal_meaning_section = page.locator('.card').filter(has_text=re.compile(r'Literal Meaning', re.IGNORECASE))
        
        # Add a language
        add_lang_btn = literal_meaning_section.locator('.add-literal-meaning-language-btn')
        add_lang_btn.click()
        
        # Fill the content
        text_area = literal_meaning_section.locator('textarea').first
        text_area.fill('sun-flower')
        
        # Verify content
        expect(text_area).to_have_value('sun-flower')

    def test_exemplar_field_visible_in_sense(self, page: Page) -> None:
        """Test that exemplar field is visible in sense cards."""
        # Scroll down to see the sense section
        page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        page.wait_for_timeout(500)
        
        # Exemplar section should be visible in sense
        exemplar_label = page.locator('label').filter(has_text='Exemplar').first
        expect(exemplar_label).to_be_visible()
        
        # Should have an Add Language button
        add_lang_btn = page.locator('.add-exemplar-language-btn').first
        expect(add_lang_btn).to_be_visible()
        expect(add_lang_btn).to_contain_text('Add Language')

    def test_add_exemplar_language(self, page: Page) -> None:
        """Test adding a language to exemplar field."""
        # Scroll to see sense section
        page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        page.wait_for_timeout(500)
        
        # Click Add Language button for exemplar
        add_lang_btn = page.locator('.add-exemplar-language-btn').first
        add_lang_btn.click()
        
        # A new language form group should appear
        lang_form = page.locator('.exemplar-forms .language-form-group').first
        expect(lang_form).to_be_visible()
        
        # Should have language selector
        lang_select = lang_form.locator('select.language-selector')
        expect(lang_select).to_be_visible()
        
        # Should have textarea for text
        text_area = lang_form.locator('textarea')
        expect(text_area).to_be_visible()
        
        # Should have remove button
        remove_btn = lang_form.locator('button.remove-exemplar-language-btn')
        expect(remove_btn).to_be_visible()

    def test_remove_exemplar_language(self, page: Page) -> None:
        """Test removing a language from exemplar field."""
        # Scroll to see sense section
        page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        page.wait_for_timeout(500)
        
        # Add a language first
        add_lang_btn = page.locator('.add-exemplar-language-btn').first
        add_lang_btn.click()
        
        # Verify it was added
        lang_form = page.locator('.exemplar-forms .language-form-group').first
        expect(lang_form).to_be_visible()
        
        # Click remove button
        remove_btn = lang_form.locator('button.remove-exemplar-language-btn')
        expect(remove_btn).to_be_visible()
        
        # Handle confirmation dialog
        page.on('dialog', lambda dialog: dialog.accept())
        remove_btn.click()
        
        # Wait for removal
        page.wait_for_timeout(500)
        
        # Language form should be removed - check count instead of element visibility
        expect(page.locator('.exemplar-forms .language-form-group')).to_have_count(0)

    def test_fill_exemplar_content(self, page: Page) -> None:
        """Test filling exemplar with actual content."""
        # Scroll to see sense section
        page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        page.wait_for_timeout(500)
        
        # Add a language
        add_lang_btn = page.locator('.add-exemplar-language-btn').first
        add_lang_btn.click()
        
        # Fill the content
        text_area = page.locator('.exemplar-forms textarea').first
        text_area.fill('mice')
        
        # Verify content
        expect(text_area).to_have_value('mice')

    def test_scientific_name_field_visible_in_sense(self, page: Page) -> None:
        """Test that scientific name field is visible in sense cards."""
        # Scroll to see sense section
        page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        page.wait_for_timeout(500)
        
        # Scientific Name section should be visible in sense
        scientific_name_label = page.locator('label').filter(has_text='Scientific Name').first
        expect(scientific_name_label).to_be_visible()
        
        # Should have an Add Language button
        add_lang_btn = page.locator('.add-scientific-name-language-btn').first
        expect(add_lang_btn).to_be_visible()
        expect(add_lang_btn).to_contain_text('Add Language')

    def test_add_scientific_name_language(self, page: Page) -> None:
        """Test adding a language to scientific name field."""
        # Scroll to see sense section
        page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        page.wait_for_timeout(500)
        
        # Click Add Language button for scientific name
        add_lang_btn = page.locator('.add-scientific-name-language-btn').first
        add_lang_btn.click()
        
        # A new language form group should appear
        lang_form = page.locator('.scientific-name-forms .language-form-group').first
        expect(lang_form).to_be_visible()
        
        # Should have language selector
        lang_select = lang_form.locator('select.language-selector')
        expect(lang_select).to_be_visible()
        
        # Should have textarea for text
        text_area = lang_form.locator('textarea')
        expect(text_area).to_be_visible()
        
        # Should have remove button
        remove_btn = lang_form.locator('button.remove-scientific-name-language-btn')
        expect(remove_btn).to_be_visible()

    def test_remove_scientific_name_language(self, page: Page) -> None:
        """Test removing a language from scientific name field."""
        # Scroll to see sense section
        page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        page.wait_for_timeout(500)
        
        # Add a language first
        add_lang_btn = page.locator('.add-scientific-name-language-btn').first
        add_lang_btn.click()
        
        # Verify it was added
        lang_form = page.locator('.scientific-name-forms .language-form-group').first
        expect(lang_form).to_be_visible()
        
        # Click remove button
        remove_btn = lang_form.locator('button.remove-scientific-name-language-btn')
        expect(remove_btn).to_be_visible()
        
        # Handle confirmation dialog
        page.on('dialog', lambda dialog: dialog.accept())
        remove_btn.click()
        
        # Wait for removal
        page.wait_for_timeout(500)
        
        # Language form should be removed - check count instead of element visibility
        expect(page.locator('.scientific-name-forms .language-form-group')).to_have_count(0)

    def test_fill_scientific_name_content(self, page: Page) -> None:
        """Test filling scientific name with actual content."""
        # Scroll to see sense section
        page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        page.wait_for_timeout(500)
        
        # Add a language
        add_lang_btn = page.locator('.add-scientific-name-language-btn').first
        add_lang_btn.click()
        
        # Fill the content
        text_area = page.locator('.scientific-name-forms textarea').first
        text_area.fill('Helianthus annuus')
        
        # Verify content
        expect(text_area).to_have_value('Helianthus annuus')

    def test_add_multiple_languages_to_literal_meaning(self, page: Page) -> None:
        """Test adding multiple languages to literal meaning."""
        # Find literal meaning section
        literal_meaning_section = page.locator('.card').filter(has_text=re.compile(r'Literal Meaning', re.IGNORECASE))
        
        # Add first language
        add_lang_btn = literal_meaning_section.locator('.add-literal-meaning-language-btn')
        add_lang_btn.click()
        page.wait_for_timeout(200)
        
        # Add second language
        add_lang_btn.click()
        page.wait_for_timeout(200)
        
        # Should have two language form groups
        lang_forms = literal_meaning_section.locator('.language-form-group')
        expect(lang_forms).to_have_count(2)

    def test_all_custom_fields_visible_together(self, page: Page) -> None:
        """Test that all three custom fields are visible simultaneously."""
        # Literal meaning at entry level
        literal_meaning_section = page.locator('.card').filter(has_text=re.compile(r'Literal Meaning', re.IGNORECASE))
        expect(literal_meaning_section).to_be_visible()
        
        # Exemplar in sense
        exemplar_label = page.locator('label').filter(has_text=re.compile(r'^Exemplar$', re.IGNORECASE)).first
        expect(exemplar_label).to_be_visible()
        
        # Scientific Name in sense
        scientific_name_label = page.locator('label').filter(has_text=re.compile(r'Scientific Name', re.IGNORECASE)).first
        expect(scientific_name_label).to_be_visible()

    def test_custom_fields_have_help_text(self, page: Page) -> None:
        """Test that custom fields have informative help text."""
        # Literal meaning help text
        literal_meaning_section = page.locator('.card').filter(has_text=re.compile(r'Literal Meaning', re.IGNORECASE))
        literal_help = literal_meaning_section.locator('.form-text')
        expect(literal_help).to_be_visible()
        expect(literal_help).to_contain_text('literal')
        
        # Find exemplar section by looking for its container
        exemplar_container = page.locator('.mb-3').filter(has=page.locator('label').filter(has_text=re.compile(r'^Exemplar$', re.IGNORECASE)))
        exemplar_help = exemplar_container.locator('.form-text').first
        expect(exemplar_help).to_be_visible()
        
        # Find scientific name section by looking for its container
        scientific_container = page.locator('.mb-3').filter(has=page.locator('label').filter(has_text=re.compile(r'Scientific Name', re.IGNORECASE)))
        scientific_help = scientific_container.locator('.form-text').first
        expect(scientific_help).to_be_visible()

    def test_custom_fields_persist_after_add_another_sense(self, page: Page) -> None:
        """Test that custom fields remain visible after adding another sense."""
        # Add exemplar to first sense
        add_exemplar_btn = page.locator('.add-exemplar-language-btn').first
        add_exemplar_btn.click()
        
        # Fill it
        exemplar_text = page.locator('.exemplar-forms textarea.exemplar-text').first
        exemplar_text.fill('first sense exemplar')
        
        # Add another sense
        add_sense_btn = page.locator('#add-sense-btn')
        add_sense_btn.click()
        page.wait_for_timeout(500)
        
        # Fill second sense definition
        sense_defs = page.locator('textarea[name*="senses[1].definition"][name*=".text"]')
        if sense_defs.count() > 0:
            sense_defs.first.fill('second definition')
        
        # Both senses should have exemplar fields
        exemplar_btns = page.locator('.add-exemplar-language-btn')
        expect(exemplar_btns).to_have_count(2)
        
        # First sense's exemplar content should still be there
        first_exemplar = page.locator('.exemplar-forms textarea.exemplar-text').first
        expect(first_exemplar).to_have_value('first sense exemplar')
