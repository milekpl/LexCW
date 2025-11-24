"""
Playwright test to verify validation works correctly in the browser.
Tests project settings integration and validation behavior.
"""
import pytest
from playwright.sync_api import Page, expect


@pytest.mark.integration
def test_validation_respects_project_settings(page: Page, live_server):
    """Test that validation uses project-configured source/target languages."""
    # Navigate to entry form
    page.goto(f"{live_server.url}/entry/new")
    
    # Fill in required fields
    page.fill('input[name="id"]', 'test_validation_entry')
    page.fill('input[name="lexical_unit[gd]"]', 'test word')
    
    # Add a sense with definition
    page.click('button:has-text("Add Sense")')
    page.fill('textarea[name="senses[0][definition][en]"]', 'English definition')
    
    # Try to save - should validate
    page.click('button[type="submit"]')
    
    # Check for success or validation message
    # This depends on your actual implementation
    expect(page).not_to_have_text("Entry validation failed")


@pytest.mark.integration
def test_empty_source_language_definition_allowed(page: Page, live_server):
    """Test that empty source language definitions are allowed."""
    page.goto(f"{live_server.url}/entry/new")
    
    # Fill in basic entry info
    page.fill('input[name="id"]', 'test_empty_source_def')
    page.fill('input[name="lexical_unit[gd]"]', 'facal')  # Scots Gaelic
    
    # Add sense with empty source language definition but filled target
    page.click('button:has-text("Add Sense")')
    page.fill('textarea[name="senses[0][definition][gd]"]', '')  # Empty source
    page.fill('textarea[name="senses[0][definition][en]"]', 'word')  # Filled target
    
    # Save - should succeed
    page.click('button[type="submit"]')
    
    # Should not show validation error about empty source definition
    expect(page).not_to_have_text("Source language definition cannot be empty")


@pytest.mark.integration
def test_ipa_character_validation(page: Page, live_server):
    """Test that IPA character validation works in browser."""
    page.goto(f"{live_server.url}/entry/new")
    
    # Fill in basic info
    page.fill('input[name="id"]', 'test_ipa_validation')
    page.fill('input[name="lexical_unit[gd]"]', 'test')
    
    # Add invalid IPA pronunciation
    page.click('button:has-text("Add Pronunciation")')
    page.fill('input[name="pronunciations[seh-fonipa]"]', 'invalid@#$')
    
    # Add a valid sense
    page.click('button:has-text("Add Sense")')
    page.fill('textarea[name="senses[0][definition][en]"]', 'test definition')
    
    # Try to save
    page.click('button[type="submit"]')
    
    # Should show validation error
    expect(page).to_have_text("Invalid IPA character", timeout=5000)
