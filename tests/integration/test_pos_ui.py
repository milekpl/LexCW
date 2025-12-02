"""Test the Flask app entry form in browser to verify POS inheritance."""

import pytest
from playwright.sync_api import Page

@pytest.mark.integration
def test_pos_inheritance_ui(playwright_page: Page, live_server):
    """Test POS inheritance in the browser UI using Playwright."""
    page = playwright_page
    
    print("Opening entry form...")
    page.goto(f"{live_server.url}/entries/add")
    
    # Wait for page to load
    page.wait_for_load_state("networkidle")
    page.wait_for_selector("input.lexical-unit-text", timeout=10000)
    print("Page loaded successfully")
    
    # Fill in lexical unit
    page.locator("input.lexical-unit-text").first.fill("test")
    
    # Get POS field and required indicator
    pos_select = page.locator("#part-of-speech")
    required_indicator = page.locator("#pos-required-indicator")
    
    print(f"Initial POS required: {pos_select.get_attribute('required')}")
    print(f"Initial asterisk visible: {required_indicator.is_visible()}")
    
    # Add a sense (may need to click "Add First Sense" or "Add Sense" button)
    # Try add-first-sense-btn first (for when there are no senses)
    if page.locator("#add-first-sense-btn").is_visible():
        add_sense_button = page.locator("#add-first-sense-btn")
    else:
        add_sense_button = page.locator("#add-sense-btn")
    
    page.wait_for_selector("#add-first-sense-btn, #add-sense-btn", state="visible", timeout=5000)
    add_sense_button.click()
    page.wait_for_timeout(1000)  # Wait for sense to be added
    
    # Wait for sense to appear
    page.wait_for_selector(".sense-item", state="visible", timeout=5000)
    
    # Fill in sense definition
    sense_definition = page.locator(".sense-item .definition-text").first
    sense_definition.fill("A test definition")
    
    # Set grammatical info for the sense
    sense_pos_select = page.locator(".sense-item .dynamic-grammatical-info").first
    sense_pos_select.select_option("Noun")
    
    page.wait_for_timeout(2000)  # Wait for inheritance logic to run
    
    # Check if entry POS was inherited and field is no longer required
    print(f"After adding sense - POS value: {pos_select.get_attribute('value')}")
    print(f"After adding sense - POS required: {pos_select.get_attribute('required')}")
    print(f"After adding sense - asterisk visible: {required_indicator.is_visible()}")
    
    # Add another sense with the same POS
    page.locator("#add-sense-btn").click()
    page.wait_for_timeout(1000)
    
    sense_definitions = page.locator(".sense-item .definition-text")
    sense_definitions.nth(1).fill("Another test definition")
    
    sense_pos_selects = page.locator(".sense-item .dynamic-grammatical-info")
    sense_pos_selects.nth(1).select_option("Noun")
    
    page.wait_for_timeout(2000)
    
    print(f"After adding 2nd sense (same POS) - POS value: {pos_select.get_attribute('value')}")
    print(f"After adding 2nd sense (same POS) - POS required: {pos_select.get_attribute('required')}")
    print(f"After adding 2nd sense (same POS) - asterisk visible: {required_indicator.is_visible()}")
    
    # Change second sense to different POS
    sense_pos_selects.nth(1).select_option("Verb")
    
    page.wait_for_timeout(2000)
    
    print(f"After changing 2nd sense POS - POS value: {pos_select.get_attribute('value')}")
    print(f"After changing 2nd sense POS - POS required: {pos_select.get_attribute('required')}")
    print(f"After changing 2nd sense POS - asterisk visible: {required_indicator.is_visible()}")
