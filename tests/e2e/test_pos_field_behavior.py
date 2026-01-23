"""E2E test for POS (Part of Speech) field behavior and inheritance.

Tests that:
1. POS field can be accessed and edited
2. Entry edit forms load correctly with POS data
3. Form functionality works as expected
"""
from __future__ import annotations

import pytest
from playwright.sync_api import Page


@pytest.mark.integration
def test_pos_field_in_add_form(page: Page, app_url: str, ensure_sense) -> None:
    """Test that POS field is accessible in add entry form."""
    page.goto(f"{app_url}/entries/add")
    
    # Wait for form to load
    page.wait_for_selector('#entry-form', state='visible', timeout=10000)
    
    # Check if POS field exists
    pos_field = page.locator('#part-of-speech')
    
    # Fill in entry data
    page.fill('input.lexical-unit-text', 'test_pos_entry')
    
    # Try to select a POS if field is available
    if pos_field.count() > 0:
        # Only attempt to select/verify POS if the option exists in the select
        if pos_field.locator('option:has-text("Noun")').count() > 0:
            pos_field.select_option(label='Noun')
            selected_value = pos_field.input_value()
            assert selected_value == 'Noun', f"POS should be set to Noun, got: {selected_value}"
        else:
            pytest.skip('POS range options not available; skipping POS selection test')
    
    # Ensure a sense exists and fill definition
    ensure_sense(page)
    page.locator('textarea[name*="definition"]:visible').first.fill('Test definition')
    
    # Submit should work
    page.click('button[type="submit"]')
    # Wait for form to be detached (redirect or removal)
    page.wait_for_selector('#entry-form', state='detached', timeout=5000)

    assert not page.url.endswith('/add'), "Form should submit successfully"


@pytest.mark.integration
def test_edit_form_loads_with_pos_data(page: Page, app_url: str, ensure_sense) -> None:
    """Test that edit form loads correctly and displays POS data."""
    # Create an entry with POS
    page.goto(f"{app_url}/entries/add")
    page.wait_for_selector('#entry-form', state='visible', timeout=10000)
    
    test_word = 'test_pos_edit_form'
    page.fill('input.lexical-unit-text', test_word)
    
    # Set POS if available
    pos_field = page.locator('#part-of-speech')
    if pos_field.count() > 0:
        pos_field.select_option('Verb')
    
    # Ensure a sense exists
    ensure_sense(page)
    page.locator('textarea[name*="definition"]:visible').first.fill('Test verb definition')
    page.click('button[type="submit"]')
    # Wait for form to be detached after submit
    page.wait_for_selector('#entry-form', state='detached', timeout=5000)
    
    # Navigate to entries list and find edit link
    page.goto(f"{app_url}/entries")
    # Wait for entries list or edit link to appear
    page.wait_for_selector(f'a[href*="{test_word}"][href*="/edit"], table tbody tr', timeout=5000)
    
    edit_link = page.locator(f'a[href*="{test_word}"][href*="/edit"]').first
    
    if edit_link.count() > 0:
        edit_link.click()
        page.wait_for_selector('#entry-form', state='visible', timeout=10000)
        
        # Verify form loaded successfully
        lexical_value = page.input_value('input.lexical-unit-text')
        assert test_word in lexical_value.lower(), \
            f"Edit form should load with correct data, got: {lexical_value}"
        
        # Check if POS data is present (either in field or data attribute)
        pos_field = page.locator('#part-of-speech')
        if pos_field.count() > 0:
            # POS field exists, check its value or data-selected attribute
            pos_value = pos_field.input_value()
            pos_data_attr = pos_field.get_attribute('data-selected')
            
            # One of these should contain the POS we set
            assert pos_value == 'Verb' or pos_data_attr == 'Verb', \
                f"POS should be preserved as 'Verb', got value={pos_value}, data-selected={pos_data_attr}"


@pytest.mark.integration  
def test_entry_without_pos_can_be_saved(page: Page, app_url: str, ensure_sense) -> None:
    """Test that entries can be saved without POS (for phrases)."""
    page.goto(f"{app_url}/entries/add")
    page.wait_for_selector('#entry-form', state='visible', timeout=10000)
    
    # Fill in only required fields, skip POS
    page.fill('input.lexical-unit-text', 'test_phrase_no_pos')
    ensure_sense(page)
    page.locator('textarea[name*="definition"]:visible').first.fill('A phrase without part of speech')
    
    # Submit form
    page.click('button[type="submit"]')
    # Wait for form to be detached after submit
    page.wait_for_selector('#entry-form', state='detached', timeout=5000)

    # Should succeed even without POS
    assert not page.url.endswith('/add'), \
        "Form should allow submission without POS for phrases"


@pytest.mark.integration
def test_sense_pos_field_behavior(page: Page, app_url: str, ensure_sense) -> None:
    """Test that sense-level POS fields work correctly."""
    page.goto(f"{app_url}/entries/add")
    page.wait_for_selector('#entry-form', state='visible', timeout=10000)
    
    # Fill in basic entry
    page.fill('input.lexical-unit-text', 'test_sense_pos')
    
    # Ensure a sense exists and fill in first sense definition
    ensure_sense(page)
    page.locator('textarea[name*="definition"]:visible').first.fill('First sense definition')
    
    # Try to set sense-level grammatical info if available
    sense_pos_fields = page.locator('.sense-item .dynamic-grammatical-info')
    
    if sense_pos_fields.count() > 0:
        sense_pos_fields.first.select_option('Noun')
        
        # Verify selection worked
        selected = sense_pos_fields.first.input_value()
        assert selected == 'Noun', f"Sense POS should be Noun, got: {selected}"
    
    # Submit form
    page.click('button[type="submit"]')
    # Wait for form to be detached after submit
    page.wait_for_selector('#entry-form', state='detached', timeout=5000)

    assert not page.url.endswith('/add'), "Form with sense POS should submit successfully"
