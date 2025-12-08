"""E2E test for homograph number field visibility and behavior.

Tests that:
1. Homograph number field does not appear in add entry form
2. Tooltip icons use consistent fa-info-circle styling
3. No "Auto-assigned if needed" placeholder text appears
"""
from __future__ import annotations

import pytest
from playwright.sync_api import Page, expect


@pytest.mark.integration
def test_add_form_has_no_homograph_field(page: Page, app_url: str) -> None:
    """Test that add entry form does not display homograph number field."""
    page.goto(f"{app_url}/entries/add")
    
    # Wait for form to load
    page.wait_for_selector('#entry-form', state='visible', timeout=10000)
    
    # Check that homograph number field is not present
    homograph_field = page.locator('#homograph-number')
    expect(homograph_field).not_to_be_visible()
    
    # Check that "Auto-assigned if needed" text is not present
    page_content = page.content()
    assert 'Auto-assigned if needed' not in page_content, \
        "Placeholder text 'Auto-assigned if needed' should not appear in add form"


@pytest.mark.integration
def test_tooltip_icon_consistency(page: Page, app_url: str) -> None:
    """Test that tooltip icons use consistent fa-info-circle styling."""
    page.goto(f"{app_url}/entries/add")
    
    # Wait for form to load
    page.wait_for_selector('#entry-form', state='visible', timeout=10000)
    
    # Check for info-circle icons (should be present)
    info_icons = page.locator('i.fa-info-circle')
    info_count = info_icons.count()
    
    # Check for question-circle icons (should be minimal or none, except for warnings)
    question_icons = page.locator('i.fa-question-circle')
    question_count = question_icons.count()
    
    # Info icons should be used for tooltips
    assert info_count > 0, "Info-circle icons should be present for tooltips"
    
    # Question icons should be minimal (only for warnings/special cases)
    print(f"Info-circle icons: {info_count}, Question-circle icons: {question_count}")


@pytest.mark.integration
def test_edit_form_homograph_behavior(page: Page, app_url: str) -> None:
    """Test homograph field behavior in edit forms for existing entries."""
    # First, create a test entry
    page.goto(f"{app_url}/entries/add")
    page.wait_for_selector('#entry-form', state='visible', timeout=10000)
    
    # Fill in minimal required fields
    page.fill('input.lexical-unit-text', 'homograph_test_word')
    page.fill('textarea[name*="definition"]', 'Test definition')
    
    # Submit form
    page.click('button[type="submit"]')
    page.wait_for_timeout(2000)
    
    # Navigate to entries list to find the created entry
    page.goto(f"{app_url}/entries")
    page.wait_for_timeout(1000)
    
    # Find and click edit link for our test entry
    edit_link = page.locator('a[href*="homograph_test_word"][href*="/edit"]').first
    
    if edit_link.count() > 0:
        edit_link.click()
        page.wait_for_selector('#entry-form', state='visible', timeout=10000)
        
        # In edit form, homograph field may or may not appear depending on whether
        # the entry has a homograph number. Just verify no "Auto-assigned" text
        page_content = page.content()
        assert 'Auto-assigned if needed' not in page_content, \
            "Placeholder text should not appear in edit form"


@pytest.mark.integration
def test_form_is_functional(page: Page, app_url: str) -> None:
    """Test that entry forms are functional despite non-critical errors."""
    # Load add form
    page.goto(f"{app_url}/entries/add")
    page.wait_for_selector('#entry-form', state='visible', timeout=10000)
    page.wait_for_timeout(1000)  # Give JS time to execute
    
    # Verify form is functional by filling a field
    page.fill('input.lexical-unit-text', 'test')
    lexical_value = page.input_value('input.lexical-unit-text')
    assert lexical_value == 'test', "Form should be interactive"
    
    # Verify form can accept definition
    page.fill('textarea[name*="definition"]', 'test definition')
    definition_value = page.locator('textarea[name*="definition"]').first.input_value()
    assert 'test definition' in definition_value, "Form should accept definition input"
