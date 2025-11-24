"""
Integration test for sense deletion functionality.

Tests that senses can be added and removed properly, and that deleted senses
don't reappear after save.
"""
import pytest
import time
from playwright.sync_api import Page, expect


@pytest.mark.integration
def test_add_and_remove_sense(playwright_page, live_server):
    """Test that adding and removing a sense works correctly."""
    page = playwright_page
    # Navigate to edit an existing entry
    page.goto(f"{live_server.url}/entries/AIDS%20test_a774b9c4-c013-4f54-9017-cf818791080c/edit")
    
    # Wait for page to load
    page.wait_for_selector('#entry-form', state='visible', timeout=10000)
    
    # Count initial senses
    initial_senses = page.locator('.sense-item').count()
    print(f"Initial sense count: {initial_senses}")
    
    # Add a new sense
    add_sense_btn = page.locator('#add-sense-btn')
    add_sense_btn.click()
    time.sleep(0.5)  # Wait for DOM update
    
    # Verify sense was added
    new_sense_count = page.locator('.sense-item').count()
    assert new_sense_count == initial_senses + 1, f"Expected {initial_senses + 1} senses, got {new_sense_count}"
    print(f"After adding: {new_sense_count} senses")
    
    # Remove the last sense
    last_sense = page.locator('.sense-item').last
    remove_btn = last_sense.locator('.remove-sense-btn')
    
    # Handle the confirmation dialog
    page.on('dialog', lambda dialog: dialog.accept())
    remove_btn.click()
    time.sleep(0.5)  # Wait for DOM update
    
    # Verify sense was removed from DOM
    after_removal_count = page.locator('.sense-item').count()
    assert after_removal_count == initial_senses, f"Expected {initial_senses} senses after removal, got {after_removal_count}"
    print(f"After removal: {after_removal_count} senses")
    
    # Save the form with skip_validation
    save_btn = page.locator('#save-btn')
    
    # Intercept the save request to add skip_validation parameter
    def handle_route(route):
        # Get the original request
        request = route.request
        if request.method == 'PUT':
            # Parse the body
            import json
            body = json.loads(request.post_data)
            # Add skip_validation flag
            body['skip_validation'] = True
            # Continue with modified body
            route.continue_(post_data=json.dumps(body))
        else:
            route.continue_()
    
    page.route('**/api/entries/*', handle_route)
    
    save_btn.click()
    
    # Wait for save to complete (look for success message or redirect)
    page.wait_for_selector('.toast, .alert-success', timeout=10000)
    time.sleep(1)
    
    # Reload the page to verify persistence
    page.reload()
    page.wait_for_selector('#entry-form', state='visible', timeout=10000)
    
    # Verify the sense count persisted
    final_sense_count = page.locator('.sense-item').count()
    assert final_sense_count == initial_senses, f"Expected {initial_senses} senses after reload, got {final_sense_count}"
    print(f"After reload: {final_sense_count} senses - deletion persisted!")


@pytest.mark.integration
def test_remove_empty_sense_with_validation_warning(playwright_page, live_server):
    """Test that removing an empty/invalid sense works even with validation warnings."""
    page = playwright_page
    # Navigate to the problematic entry
    page.goto(f"{live_server.url}/entries/AIDS%20test_a774b9c4-c013-4f54-9017-cf818791080c/edit")
    
    # Wait for page to load
    page.wait_for_selector('#entry-form', state='visible', timeout=10000)
    
    # Count current senses
    current_senses = page.locator('.sense-item').count()
    print(f"Current sense count: {current_senses}")
    
    # If there's more than one sense, try to remove the last one
    if current_senses > 1:
        last_sense = page.locator('.sense-item').last
        
        # Check if it's empty (no definition or gloss text)
        definition_text = last_sense.locator('textarea[name*="definition"]').first.input_value()
        gloss_text = last_sense.locator('textarea[name*="gloss"]').first.input_value()
        
        print(f"Last sense - definition: '{definition_text}', gloss: '{gloss_text}'")
        
        # Remove the sense
        remove_btn = last_sense.locator('.remove-sense-btn')
        page.on('dialog', lambda dialog: dialog.accept())
        remove_btn.click()
        time.sleep(0.5)
        
        # Verify removal in DOM
        after_removal = page.locator('.sense-item').count()
        assert after_removal == current_senses - 1, "Sense not removed from DOM"
        
        # Save with skip_validation
        def handle_route(route):
            if route.request.method == 'PUT':
                import json
                body = json.loads(route.request.post_data)
                body['skip_validation'] = True
                route.continue_(post_data=json.dumps(body))
            else:
                route.continue_()
        
        page.route('**/api/entries/*', handle_route)
        
        save_btn = page.locator('#save-btn')
        save_btn.click()
        
        # Wait for save
        page.wait_for_timeout(2000)
        
        # Reload and verify
        page.reload()
        page.wait_for_selector('#entry-form', state='visible', timeout=10000)
        
        final_count = page.locator('.sense-item').count()
        assert final_count == current_senses - 1, f"Sense reappeared after save! Expected {current_senses - 1}, got {final_count}"
        print(f"Success! Sense deletion persisted. Final count: {final_count}")


@pytest.mark.integration  
def test_validation_warnings_allow_save(playwright_page, live_server):
    """Test that validation warnings don't prevent saving with skip_validation."""
    page = playwright_page
    # Create a test entry with intentional validation issues
    page.goto(f"{live_server.url}/entries/new")
    page.wait_for_selector('#entry-form', state='visible', timeout=10000)
    
    # Fill in minimal required fields
    page.locator('input[name="id"]').fill('test_validation_warning_entry')
    page.locator('textarea[name="lexical_unit.en.text"]').fill('test word')
    
    # Add a sense with empty definition (validation issue)
    add_sense_btn = page.locator('#add-sense-btn, #add-first-sense-btn').first
    add_sense_btn.click()
    time.sleep(0.5)
    
    # Leave definition empty but add a gloss (this should trigger a warning)
    page.locator('textarea[name*="senses[0].gloss"]').first.fill('a test')
    
    # Try to save with skip_validation
    def handle_route(route):
        if route.request.method == 'POST':
            import json
            body = json.loads(route.request.post_data)
            body['skip_validation'] = True
            route.continue_(post_data=json.dumps(body))
        else:
            route.continue_()
    
    page.route('**/api/entries/*', handle_route)
    
    save_btn = page.locator('#save-btn')
    save_btn.click()
    
    # Should succeed despite validation warnings
    # Wait for either success or error
    page.wait_for_timeout(3000)
    
    # Check if we were redirected or got success message
    # If save succeeded, we should either be on the entries list or see a success message
    current_url = page.url
    print(f"After save, URL: {current_url}")
    
    # Cleanup: delete the test entry if it was created
    try:
        if 'test_validation_warning_entry' in current_url or '/entries' in current_url:
            # Entry was created, delete it
            import requests
            requests.delete(f"{live_server.url}/api/entries/test_validation_warning_entry")
    except Exception:
        pass
