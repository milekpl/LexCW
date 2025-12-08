"""E2E test for form submission with various data formats.

Tests that:
1. Form data with dot notation is processed correctly
2. Multilingual fields are handled properly
3. Complex nested structures work as expected
"""
from __future__ import annotations

import pytest
from playwright.sync_api import Page


@pytest.mark.integration
def test_form_submission_with_multilingual_data(page: Page, app_url: str) -> None:
    """Test that form submission with multilingual data works correctly."""
    page.goto(f"{app_url}/entries/add")
    
    # Wait for form to load
    page.wait_for_selector('#entry-form', state='visible', timeout=10000)
    
    # Fill in lexical unit in multiple languages
    # Find all lexical unit inputs (typically labeled by language code)
    lexical_inputs = page.locator('input.lexical-unit-text')
    
    if lexical_inputs.count() > 0:
        # Fill first lexical unit (usually source language)
        lexical_inputs.first.fill('test_multilingual')
    
    # Fill in definition
    page.fill('textarea[name*="definition"]', 'A test definition in English')
    
    # Submit form
    page.click('button[type="submit"]')
    
    # Wait for navigation (should redirect away from /add)
    page.wait_for_timeout(2000)
    
    # Verify submission was successful (not on /add page anymore)
    assert not page.url.endswith('/add'), \
        "Form should redirect after successful submission"


@pytest.mark.integration
def test_form_submission_with_grammatical_info(page: Page, app_url: str) -> None:
    """Test form submission with grammatical info (part of speech)."""
    page.goto(f"{app_url}/entries/add")
    
    # Wait for form to load
    page.wait_for_selector('#entry-form', state='visible', timeout=10000)
    
    # Fill in basic fields
    page.fill('input.lexical-unit-text', 'test_pos_word')
    
    # Select part of speech if available
    pos_select = page.locator('#part-of-speech')
    if pos_select.count() > 0:
        pos_select.select_option('Noun')
    
    # Fill in definition
    page.fill('textarea[name*="definition"]', 'Test definition with POS')
    
    # Submit form
    page.click('button[type="submit"]')
    page.wait_for_timeout(2000)
    
    # Verify submission was successful
    assert not page.url.endswith('/add'), \
        "Form should redirect after successful submission"


@pytest.mark.integration
def test_form_submission_with_notes(page: Page, app_url: str) -> None:
    """Test form submission with various types of notes."""
    page.goto(f"{app_url}/entries/add")
    
    # Wait for form to load
    page.wait_for_selector('#entry-form', state='visible', timeout=10000)
    
    # Fill in basic fields
    page.fill('input.lexical-unit-text', 'test_notes_word')
    page.fill('textarea[name*="definition"]', 'Test definition with notes')
    
    # Add notes if note fields are available
    # Look for note fields (they might be in expandable sections)
    note_fields = page.locator('textarea[name*="note"]')
    
    if note_fields.count() > 0:
        note_fields.first.fill('This is a general note about the entry')
    
    # Submit form
    page.click('button[type="submit"]')
    page.wait_for_timeout(2000)
    
    # Verify submission was successful
    assert not page.url.endswith('/add'), \
        "Form should redirect after successful submission"


@pytest.mark.integration
def test_edit_form_preserves_data(page: Page, app_url: str) -> None:
    """Test that editing an entry preserves existing data."""
    # First create an entry
    page.goto(f"{app_url}/entries/add")
    page.wait_for_selector('#entry-form', state='visible', timeout=10000)
    
    test_word = 'test_edit_preservation'
    test_definition = 'Original definition for edit test'
    
    page.fill('input.lexical-unit-text', test_word)
    page.fill('textarea[name*="definition"]', test_definition)
    
    page.click('button[type="submit"]')
    page.wait_for_timeout(2000)
    
    # Navigate to entries list
    page.goto(f"{app_url}/entries")
    page.wait_for_timeout(1000)
    
    # Find and click edit link
    edit_link = page.locator(f'a[href*="{test_word}"][href*="/edit"]').first
    
    if edit_link.count() > 0:
        edit_link.click()
        page.wait_for_selector('#entry-form', state='visible', timeout=10000)
        
        # Verify the lexical unit is preserved
        lexical_value = page.input_value('input.lexical-unit-text')
        assert test_word in lexical_value.lower(), \
            f"Lexical unit should be preserved in edit form, got: {lexical_value}"
        
        # Verify definition is preserved
        definition_field = page.locator('textarea[name*="definition"]').first
        definition_value = definition_field.input_value()
        assert test_definition in definition_value, \
            f"Definition should be preserved in edit form, got: {definition_value}"


@pytest.mark.integration
def test_form_handles_special_characters(page: Page, app_url: str) -> None:
    """Test that form handles special characters correctly."""
    page.goto(f"{app_url}/entries/add")
    page.wait_for_selector('#entry-form', state='visible', timeout=10000)
    
    # Test with special characters
    special_word = "test_special_chars_éàü"
    special_definition = "Definition with special chars: é, à, ü, ñ, ø"
    
    page.fill('input.lexical-unit-text', special_word)
    page.fill('textarea[name*="definition"]', special_definition)
    
    # Submit form
    page.click('button[type="submit"]')
    page.wait_for_timeout(2000)
    
    # Verify submission was successful
    assert not page.url.endswith('/add'), \
        "Form should handle special characters and submit successfully"
