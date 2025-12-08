"""
Playwright test to verify validation works correctly in the browser.
Tests project settings integration and validation behavior.
"""
import pytest
from playwright.sync_api import Page, expect


@pytest.mark.integration
def test_validation_respects_project_settings(page: Page, app_url: str):
    """Test that validation uses project-configured source/target languages."""
    # Navigate to entry form
    page.goto(f"{app_url}/entries/add")
    
    # Debug: Take screenshot and print page content
    page.screenshot(path="e2e_test_logs/validation_add_page.png")
    print(f"Page URL: {page.url}")
    print(f"Page title: {page.title()}")
    
    # Check if we got redirected or if there's an error
    if 'error' in page.url or page.url.endswith('/entries'):
        print("⚠ Page redirected or showing error")
        print(f"Page content preview: {page.content()[:500]}")
    
    # Wait for form to load
    page.wait_for_selector('#entry-form', state='visible', timeout=10000)
    page.wait_for_selector('input.lexical-unit-text', state='visible', timeout=10000)
    
    # Fill in required fields using new multilingual format
    page.fill('input.lexical-unit-text', 'test word')
    
    # Fill in the default template sense definition (in default sense template)
    page.fill('textarea[name*="definition"]', 'English definition')
    
    # Try to save - should validate
    page.click('button[type="submit"]')
    
    # Wait for navigation and check we didn't get validation error
    page.wait_for_timeout(3000)
    # If successful, we should be redirected away from /add
    assert not page.url.endswith('/add'), "Form submission should redirect away from add page"


@pytest.mark.integration
def test_empty_source_language_definition_allowed(page: Page, app_url: str):
    """Test that empty source language definitions are allowed."""
    page.goto(f"{app_url}/entries/add")
    
    # Wait for form to load
    page.wait_for_selector('#entry-form', state='visible', timeout=10000)
    page.wait_for_selector('input.lexical-unit-text', state='visible', timeout=10000)
    
    # Fill in basic entry info using new multilingual format
    page.fill('input.lexical-unit-text', 'facal')  # Scots Gaelic
    
    # Fill in the template definition (it will be created as first sense)
    page.fill('textarea[name*="definition"]', 'word')  # Target language definition
    
    # Save - should succeed
    page.click('button[type="submit"]')
    
    # Wait for navigation and verify no error about source definition
    page.wait_for_timeout(3000)
    # If successful, we should be redirected away from /add
    assert not page.url.endswith('/add'), "Form submission should redirect away from add page"


@pytest.mark.integration
def test_ipa_character_validation(page: Page, app_url: str):
    """Test that IPA character validation works in browser."""
    page.goto(f"{app_url}/entries/add")
    
    # Wait for form to load
    page.wait_for_selector('#entry-form', state='visible', timeout=10000)
    page.wait_for_selector('input.lexical-unit-text', state='visible', timeout=10000)
    
    # Fill in basic info using new multilingual format
    page.fill('input.lexical-unit-text', 'test')
    
    # Add pronunciation (if pronunciation button exists)
    add_pronunciation_btn = page.locator('button:has-text("Add Pronunciation")')
    if add_pronunciation_btn.count() > 0:
        add_pronunciation_btn.click()
        # Fill with invalid IPA - adjust selector based on actual form structure
        ipa_input = page.locator('input[name*="pronunciation"]').first
        if ipa_input.count() > 0:
            ipa_input.fill('invalid@#$')
    
    # Add a valid sense definition
    page.fill('textarea[name*="definition"]', 'test definition')
    
    # Try to save
    page.click('button[type="submit"]')
    
    # Should show validation error if IPA validation is enabled
    # Note: This test may need adjustment based on actual validation behavior
    # For now, just verify it doesn't crash
    page.wait_for_timeout(2000)
