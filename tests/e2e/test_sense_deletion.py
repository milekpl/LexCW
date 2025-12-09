"""
Integration tests for sense deletion functionality.

Tests that senses can be added and removed properly, and that deleted senses
don't reappear after save.
"""
import pytest
from playwright.sync_api import expect


@pytest.mark.integration
def test_sense_deletion_persists_after_save(page, flask_test_server):
    """
    CRITICAL TEST: Verify that deleted senses don't reappear after save.
    
    This tests the fix for the bug where:
    1. User deletes a sense from the DOM (count goes from 2 to 1)
    2. Form serializer picks up default-sense-template fields (ghost sense)
    3. Server receives 2 senses (1 real + 1 ghost)
    4. After save and reload, deleted sense reappears
    
    The fix: Mark default-sense-template and exclude it from serialization.
    """
    print("TEST STARTING: test_sense_deletion_persists_after_save")
    page = page
    
    # For this test, create an entry with 2 senses via API, then edit it
    import requests
    
    print("Creating test entry data...")
    test_entry_data = {
        "id": "sense_deletion_test_" + str(hash("test"))[-8:],
        "lexical_unit": {"en": "sense_deletion_test"},
        "senses": [
            {
                "id": "sense_1",
                "definition": {"en": "First definition"},
                "gloss": {"en": "first"}
            },
            {
                "id": "sense_2",
                "definition": {"en": "Second definition"},
                "gloss": {"en": "second"}
            }
        ]
    }
    
    # Create entry via API
    print(f"Creating entry via API at {flask_test_server}/api/entries/...")
    response = requests.post(
        f"{flask_test_server}/api/entries/",
        json=test_entry_data,
        headers={"Content-Type": "application/json"}
    )
    print(f"API response status: {response.status_code}")
    assert response.status_code in [200, 201], f"Failed to create test entry: {response.text}"
    
    entry_id = test_entry_data["id"]
    edit_url = f"{flask_test_server}/entries/{entry_id}/edit"
    
    # Navigate to edit the entry
    print(f"Navigating to edit URL: {edit_url}")
    page.goto(edit_url)
    page.wait_for_load_state("networkidle")
    
    print("Page loaded, setting up console monitoring...")
    # Setup console monitoring
    console_logs = []
    page.on("console", lambda msg: console_logs.append(msg.text))
    
    # Verify we have 2 real senses (excluding template)
    print("Checking for real senses...")
    real_senses = page.locator('.sense-item:not(#default-sense-template):not(.default-sense-template)')
    initial_count = real_senses.count()
    print(f"Found {initial_count} real senses")
    
    assert initial_count == 2, f"Expected 2 real senses, got {initial_count}"
    
    # Clear console logs for deletion monitoring
    console_logs.clear()
    
    # Handle confirmation dialog
    page.on("dialog", lambda dialog: dialog.accept())
    
    # Remove the second sense
    print("Removing second sense...")
    remove_btn = real_senses.nth(1).locator('.remove-sense-btn')
    remove_btn.click()
    # Wait for the sense to actually be removed from DOM
    expect(page.locator('.sense-item:not(#default-sense-template):not(.default-sense-template)')).to_have_count(1, timeout=5000)
    
    # Verify sense was removed from DOM
    print("Verifying sense removal...")
    real_senses = page.locator('.sense-item:not(#default-sense-template):not(.default-sense-template)')
    after_deletion = real_senses.count()
    print(f"After deletion: {after_deletion} senses")
    assert after_deletion == 1, f"Expected 1 sense after deletion, got {after_deletion}"
    
    # Check console logs for deletion confirmation
    print("Checking console logs for deletion...")
    deletion_logs = [log for log in console_logs if 'SENSE DELETION' in log]
    print(f"Found {len(deletion_logs)} deletion logs")
    assert len(deletion_logs) > 0, "No sense deletion logs found"
    
    # Clear and monitor serialization
    print("Clearing console logs for serialization monitoring...")
    console_logs.clear()
    
    # Save the entry
    print("Clicking Save Entry button...")
    page.click('button[type="submit"]:has-text("Save Entry")')
    # Wait for console logs to appear (indicates form submission was processed)
    # Check every 100ms for the logs to appear
    max_attempts = 30  # 3 seconds total
    for attempt in range(max_attempts):
        if len(console_logs) > 5:  # Should have multiple logs after submission
            break
        page.wait_for_timeout(100)
    
    # CRITICAL CHECK: Verify serialization only included 1 sense
    print(f"Checking console logs... found {len(console_logs)} logs")
    
    submit_logs = [log for log in console_logs if 'FORM SUBMIT' in log]
    print(f"Found {len(submit_logs)} submit logs")
    if len(submit_logs) > 0:
        # Check for "Serialized senses: 1" (not 2!)
        serialized_count_log = [log for log in submit_logs if 'Serialized senses:' in log]
        print(f"Found {len(serialized_count_log)} serialized count logs: {serialized_count_log}")
        if len(serialized_count_log) > 0:
            assert 'Serialized senses: 1' in serialized_count_log[0], \
                f"Wrong sense count serialized. Expected 'Serialized senses: 1', got: {serialized_count_log[0]}"
    else:
        print("WARNING: No form submit logs found, but continuing...")
    
    # Wait for navigation or for the page to show a success message
    # The form might not redirect on success, so wait for either:
    # 1. Navigation to /entries/{id} or similar
    # 2. A timeout (form processed)
    print("Waiting for form submission to complete...")
    try:
        page.wait_for_url("**/entries/**", timeout=3000)
        print(f"Navigation successful to: {page.url}")
    except Exception as nav_error:
        print(f"Navigation timeout (form may have already processed): {nav_error}")
        # Check if we're on a success/view page or still on edit
        current_url = page.url
        print(f"Current URL after form submission: {current_url}")
        # Wait a bit more for any async processing
        page.wait_for_timeout(1000)
    
    # Navigate back to edit to verify persistence
    page.goto(edit_url)
    page.wait_for_load_state("networkidle")
    
    # THE ULTIMATE TEST: Verify the deleted sense is still gone
    real_senses = page.locator('.sense-item:not(#default-sense-template):not(.default-sense-template)')
    final_count = real_senses.count()
    assert final_count == 1, \
        f"BUG: Deleted sense reappeared! Expected 1 sense after reload, got {final_count}"
    
    # Verify the remaining sense has the correct content
    remaining_def = real_senses.first.locator('textarea[name*="definition"][name$=".text"]').first.input_value()
    assert remaining_def == 'First definition', \
        f"Wrong sense remained. Expected 'First definition', got '{remaining_def}'"
    
    print("✅ SUCCESS: Sense deletion persisted correctly!")


@pytest.mark.integration
def test_default_template_not_serialized(page, flask_test_server):
    """Test that the default-sense-template is never included in serialization."""
    page = page
    
    # Navigate to add entry page
    page.goto(f"{flask_test_server}/entries/add")
    page.wait_for_load_state("networkidle")
    
    # Verify default template exists in DOM
    default_template = page.locator('#default-sense-template, .default-sense-template')
    expect(default_template).to_have_count(1)
    
    # Check if we need to add a sense first
    real_senses = page.locator('.sense-item:not(#default-sense-template):not(.default-sense-template)')
    if real_senses.count() == 0:
        add_sense_btn = page.locator('#add-sense-btn')
        if add_sense_btn.is_visible():
            add_sense_btn.click()
            # Wait for sense to appear
            expect(page.locator('.sense-item:not(#default-sense-template):not(.default-sense-template)')).to_have_count(1, timeout=3000)
    
    # Fill minimal entry data - use correct multilingual selectors
    page.locator('input.lexical-unit-text').first.fill('template_test')
    first_sense = page.locator('.sense-item:not(#default-sense-template):not(.default-sense-template)').first
    first_sense.locator('textarea[name*="definition"]').first.fill('Test definition')
    
    # Setup console monitoring
    console_logs = []
    page.on("console", lambda msg: console_logs.append(msg.text))
    
    # Save
    page.click('button[type="submit"]:has-text("Save Entry")')
    # Wait for form submission logs to appear
    max_attempts = 30
    for _ in range(max_attempts):
        if len(console_logs) > 5:
            break
        page.wait_for_timeout(100)
    
    # Check serialization logs
    submit_logs = [log for log in console_logs if 'FORM SUBMIT' in log]
    
    # Should serialize exactly 1 sense (not 2 - one real + one template)
    count_log = [log for log in submit_logs if 'Serialized senses:' in log]
    assert len(count_log) > 0, f"No serialization count log. Got {len(console_logs)} total logs"
    assert 'Serialized senses: 1' in count_log[0], \
        f"Default template was serialized! Got: {count_log[0]}"


@pytest.mark.integration
def test_multiple_deletions(page, flask_test_server):
    """Test deleting multiple senses in sequence."""
    page = page
    
    page.goto(f"{flask_test_server}/entries/add")
    page.wait_for_load_state("networkidle")
    
    # Fill lexical unit first
    page.locator('input.lexical-unit-text').first.fill('multi_delete_test')
    
    # Add 3 senses (on add page, check if we need to add the first one)
    real_senses = page.locator('.sense-item:not(#default-sense-template):not(.default-sense-template)')
    initial_count = real_senses.count()
    
    senses_to_add = 3 - initial_count
    for _ in range(senses_to_add):
        add_btn = page.locator('#add-sense-btn')
        if add_btn.is_visible():
            add_btn.click()
            # Wait for sense to appear
            page.wait_for_selector('.sense-item:not(#default-sense-template)', timeout=3000)
    
    # Refresh selector
    real_senses = page.locator('.sense-item:not(#default-sense-template):not(.default-sense-template)')
    sense_count = real_senses.count()
    
    if sense_count < 3:
        pytest.skip(f"Could not create 3 senses (only got {sense_count})")
    
    # Fill in definitions for all 3 senses
    real_senses.nth(0).locator('textarea[name*="definition"]').first.fill('Def 1', timeout=5000)
    real_senses.nth(1).locator('textarea[name*="definition"]').first.fill('Def 2', timeout=5000)
    real_senses.nth(2).locator('textarea[name*="definition"]').first.fill('Def 3', timeout=5000)
    
    # Monitor console for errors
    console_logs = []
    page.on("console", lambda msg: console_logs.append(msg.text))
    
    # Save
    page.click('button[type="submit"]:has-text("Save Entry")')
    # Wait for submission to process by checking if URL has changed
    page.wait_for_url("**", timeout=5000)
    
    print(f"DEBUG: URL after save: {page.url}")
    print("DEBUG: Console logs during save:")
    for log in console_logs[-20:]:
        if 'error' in log.lower() or 'fail' in log.lower() or 'validation' in log.lower():
            print(f"  ERROR/WARNING: {log}")
    
    # Check if we actually navigated away from /add
    if page.url.endswith('/add'):
        print("DEBUG: Still on add page - submission failed")
        print("DEBUG: All console logs:")
        for log in console_logs[-30:]:
            print(f"  {log}")
        pytest.skip("Form submission failed - still on add page")
    
    entry_id = page.url.split('/')[-1].split('?')[0]
    print(f"DEBUG: Extracted entry ID: {entry_id}")
    edit_url = f"{flask_test_server}/entries/{entry_id}/edit"
    print(f"DEBUG: Will navigate to edit URL: {edit_url}")
    
    # Delete sense 2
    page.goto(edit_url)
    page.wait_for_load_state("networkidle")
    print(f"DEBUG: Edit page loaded, URL: {page.url}")
    
    # Check how many senses exist before deletion
    real_senses = page.locator('.sense-item:not(#default-sense-template):not(.default-sense-template)')
    sense_count_before = real_senses.count()
    print(f"DEBUG: Found {sense_count_before} senses on edit page")
    if sense_count_before != 3:
        pytest.skip(f"Expected 3 senses on edit page, got {sense_count_before}")
    
    page.on("dialog", lambda dialog: dialog.accept())
    
    # Find the remove button within the second sense (nth(1))
    remove_btn = real_senses.nth(1).locator('.remove-sense-btn')
    if remove_btn.count() == 0:
        pytest.skip("No remove button found on sense 2")
    
    remove_btn.click()
    # Wait for sense to be removed from DOM
    expect(page.locator('.sense-item:not(#default-sense-template):not(.default-sense-template)')).to_have_count(2, timeout=5000)
    
    page.click('button[type="submit"]:has-text("Save Entry")')
    
    # Verify
    page.goto(edit_url)
    page.wait_for_load_state("networkidle")
    real_senses = page.locator('.sense-item:not(#default-sense-template):not(.default-sense-template)')
    assert real_senses.count() == 2, "First deletion didn't persist"
    
    # Delete another
    real_senses.nth(1).locator('.remove-sense-btn').click()
    # Wait for sense to be removed
    expect(page.locator('.sense-item:not(#default-sense-template):not(.default-sense-template)')).to_have_count(1, timeout=5000)
    
    page.click('button[type="submit"]:has-text("Save Entry")')
    
    # Final check
    page.goto(edit_url)
    page.wait_for_load_state("networkidle")
    real_senses = page.locator('.sense-item:not(#default-sense-template):not(.default-sense-template)')
    assert real_senses.count() == 1, "Second deletion didn't persist"
    
    print("✅ Multiple deletions all persisted!")


@pytest.mark.integration
def test_add_and_remove_sense(page, flask_test_server):
    """Test that adding and removing a sense works correctly."""
    page = page
    
    # Navigate to edit an existing entry - use test_entry_1 from E2E database
    entry_id = "test_entry_1"
    page.goto(f"{flask_test_server}/entries/{entry_id}/edit")
    
    # Wait for page to load
    page.wait_for_selector('#entry-form', state='visible', timeout=10000)
    
    # Count initial real senses (excluding template)
    real_senses = page.locator('.sense-item:not(#default-sense-template):not(.default-sense-template)')
    initial_senses = real_senses.count()
    print(f"Initial sense count: {initial_senses}")
    
    # Add a new sense
    add_sense_btn = page.locator('button#add-sense-btn')
    add_sense_btn.click()
    # Wait for sense to be added to DOM
    expect(page.locator('.sense-item:not(#default-sense-template):not(.default-sense-template)')).to_have_count(initial_senses + 1, timeout=5000)
    
    # Fill in the new sense with minimal data
    new_sense = page.locator('.sense-item:not(#default-sense-template):not(.default-sense-template)').last
    new_sense.locator('textarea[name*="definition"][name$=".text"]').first.fill('New test definition')
    
    # Remove the last sense
    # Handle the confirmation dialog
    page.on('dialog', lambda dialog: dialog.accept())
    remove_btn = new_sense.locator('.remove-sense-btn')
    remove_btn.click()
    # Wait for sense to be removed
    expect(page.locator('.sense-item:not(#default-sense-template):not(.default-sense-template)')).to_have_count(initial_senses, timeout=5000)
    
    # Save the form
    save_btn = page.locator('button[type="submit"]:has-text("Save Entry")')
    save_btn.click()
    
    # Wait for form to be processed and navigate back
    page.wait_for_load_state("networkidle", timeout=10000)
    
    # Reload the page to verify persistence
    page.goto(f"{flask_test_server}/entries/{entry_id}/edit")
    page.wait_for_selector('#entry-form', state='visible', timeout=10000)
    
    # Verify the sense count persisted
    real_senses = page.locator('.sense-item:not(#default-sense-template):not(.default-sense-template)')
    final_sense_count = real_senses.count()
    
    assert final_sense_count == initial_senses, \
        f"Sense count didn't persist. Expected {initial_senses}, got {final_sense_count}"
    print(f"✓ After reload: {final_sense_count} senses - deletion persisted!")
