"""Integration test for sense deletion bug fix.

This test verifies that deleted senses stay deleted after save.
The bug was that the default-sense-template (always present in the DOM)
was being serialized along with actual senses, causing ghost senses to appear.
"""
import pytest
from playwright.sync_api import Page, expect


@pytest.mark.integration
def test_sense_deletion_persists_after_save(playwright_page, live_server):
    """
    CRITICAL TEST: Verify that deleted senses don't reappear after save.
    
    This tests the fix for the bug where:
    1. User deletes a sense from the DOM (count goes from 2 to 1)
    2. Form serializer picks up default-sense-template fields (ghost sense)
    3. Server receives 2 senses (1 real + 1 ghost)
    4. After save and reload, deleted sense reappears
    
    The fix: Mark default-sense-template and exclude it from serialization.
    """
    page = playwright_page
    
    # For this test, create an entry with 2 senses via API, then edit it
    import requests
    import json
    
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
    response = requests.post(
        f"{live_server.url}/api/entries/",
        json=test_entry_data,
        headers={"Content-Type": "application/json"}
    )
    assert response.status_code in [200, 201], f"Failed to create test entry: {response.text}"
    
    entry_id = test_entry_data["id"]
    edit_url = f"{live_server.url}/entries/{entry_id}/edit"
    
    # Navigate to edit the entry
    page.goto(edit_url)
    page.wait_for_load_state("networkidle")
    
    # Setup console monitoring
    console_logs = []
    page.on("console", lambda msg: console_logs.append(msg.text))
    
    # Verify we have 2 real senses (excluding template)
    real_senses = page.locator('.sense-item:not(#default-sense-template):not(.default-sense-template)')
    initial_count = real_senses.count()
    assert initial_count == 2, f"Expected 2 real senses, got {initial_count}"
    
    # Clear console logs for deletion monitoring
    console_logs.clear()
    
    # Handle confirmation dialog
    page.on("dialog", lambda dialog: dialog.accept())
    
    # Remove the second sense
    remove_btn = real_senses.nth(1).locator('.remove-sense-btn')
    remove_btn.click()
    page.wait_for_timeout(500)
    
    # Verify sense was removed from DOM
    real_senses = page.locator('.sense-item:not(#default-sense-template):not(.default-sense-template)')
    after_deletion = real_senses.count()
    assert after_deletion == 1, f"Expected 1 sense after deletion, got {after_deletion}"
    
    # Check console logs for deletion confirmation
    deletion_logs = [log for log in console_logs if 'SENSE DELETION' in log]
    assert len(deletion_logs) > 0, "No sense deletion logs found"
    
    # Look for the critical log showing count after removal
    count_log = [log for log in deletion_logs if 'Sense count after removal: 1' in log]
    assert len(count_log) > 0, f"Expected 'Sense count after removal: 1' in logs. Got: {deletion_logs}"
    
    # Clear and monitor serialization
    console_logs.clear()
    
    # Save the entry
    page.click('button[type="submit"]:has-text("Save Entry")')
    page.wait_for_timeout(2000)  # Wait for serialization and submission
    
    # CRITICAL CHECK: Verify serialization only included 1 sense
    submit_logs = [log for log in console_logs if 'FORM SUBMIT' in log]
    assert len(submit_logs) > 0, f"No form submit logs found. All logs: {console_logs}"
    
    # Check for "Serialized senses: 1" (not 2!)
    serialized_count_log = [log for log in submit_logs if 'Serialized senses:' in log]
    assert len(serialized_count_log) > 0, f"No serialization count log. Submit logs: {submit_logs}"
    
    # This is THE critical assertion - if this fails, the default template is still being serialized
    assert 'Serialized senses: 1' in serialized_count_log[0], \
        f"BUG NOT FIXED: Expected 'Serialized senses: 1', got: {serialized_count_log[0]}"
    
    # Wait for navigation after save
    page.wait_for_url("**/entries/**", timeout=10000)
    
    # Navigate back to edit to verify persistence
    page.goto(edit_url)
    page.wait_for_load_state("networkidle")
    
    # THE ULTIMATE TEST: Verify the deleted sense is still gone
    real_senses = page.locator('.sense-item:not(#default-sense-template):not(.default-sense-template)')
    final_count = real_senses.count()
    assert final_count == 1, \
        f"BUG: Deleted sense reappeared! Expected 1 sense after reload, got {final_count}"
    
    # Verify the remaining sense has the correct content
    remaining_def = real_senses.first.locator('textarea[name*="definition"]').first.input_value()
    assert remaining_def == 'First definition', \
        f"Wrong sense remained. Expected 'First definition', got '{remaining_def}'"
    
    print("✅ SUCCESS: Sense deletion persisted correctly!")


@pytest.mark.integration
def test_default_template_not_serialized(playwright_page, live_server):
    """Test that the default-sense-template is never included in serialization."""
    page = playwright_page
    
    # Navigate to add entry page
    page.goto(f"{live_server.url}/entries/add")
    page.wait_for_load_state("networkidle")
    
    # Verify default template exists in DOM
    default_template = page.locator('#default-sense-template, .default-sense-template')
    expect(default_template).to_have_count(1)
    
    # Fill minimal entry data
    page.fill('input[name="lexical_unit"]', 'template_test')
    page.locator('textarea[name*="definition"]').first.fill('Test definition')
    
    # Setup console monitoring
    console_logs = []
    page.on("console", lambda msg: console_logs.append(msg.text))
    
    # Save
    page.click('button[type="submit"]:has-text("Save Entry")')
    page.wait_for_timeout(2000)
    
    # Check serialization logs
    submit_logs = [log for log in console_logs if 'FORM SUBMIT' in log]
    
    # Should serialize exactly 1 sense (not 2 - one real + one template)
    count_log = [log for log in submit_logs if 'Serialized senses:' in log]
    assert len(count_log) > 0, "No serialization count log"
    assert 'Serialized senses: 1' in count_log[0], \
        f"Default template was serialized! Got: {count_log[0]}"


@pytest.mark.integration
def test_multiple_deletions(playwright_page, live_server):
    """Test deleting multiple senses in sequence."""
    page = playwright_page
    
    page.goto(f"{live_server.url}/entries/add")
    page.wait_for_load_state("networkidle")
    
    # Create entry with 3 senses
    page.fill('input[name="lexical_unit"]', 'multi_delete_test')
    page.locator('textarea[name*="definition"]').first.fill('Def 1')
    
    page.click('button:has-text("Add Sense")')
    page.wait_for_timeout(300)
    page.click('button:has-text("Add Sense")')
    page.wait_for_timeout(300)
    
    real_senses = page.locator('.sense-item:not(#default-sense-template):not(.default-sense-template)')
    real_senses.nth(1).locator('textarea[name*="definition"]').first.fill('Def 2')
    real_senses.nth(2).locator('textarea[name*="definition"]').first.fill('Def 3')
    
    # Save
    page.click('button[type="submit"]:has-text("Save Entry")')
    page.wait_for_url("**/entries/**", timeout=10000)
    
    entry_id = page.url.split('/')[-1].split('?')[0]
    edit_url = f"{live_server.url}/entries/{entry_id}/edit"
    
    # Delete sense 2
    page.goto(edit_url)
    page.wait_for_load_state("networkidle")
    
    page.on("dialog", lambda dialog: dialog.accept())
    real_senses = page.locator('.sense-item:not(#default-sense-template):not(.default-sense-template)')
    real_senses.nth(1).locator('.remove-sense-btn').click()
    page.wait_for_timeout(500)
    
    page.click('button[type="submit"]:has-text("Save Entry")')
    page.wait_for_url("**/entries/**", timeout=10000)
    
    # Verify
    page.goto(edit_url)
    page.wait_for_load_state("networkidle")
    real_senses = page.locator('.sense-item:not(#default-sense-template):not(.default-sense-template)')
    assert real_senses.count() == 2, "First deletion didn't persist"
    
    # Delete another
    real_senses.nth(1).locator('.remove-sense-btn').click()
    page.wait_for_timeout(500)
    
    page.click('button[type="submit"]:has-text("Save Entry")')
    page.wait_for_url("**/entries/**", timeout=10000)
    
    # Final check
    page.goto(edit_url)
    page.wait_for_load_state("networkidle")
    real_senses = page.locator('.sense-item:not(#default-sense-template):not(.default-sense-template)')
    assert real_senses.count() == 1, "Second deletion didn't persist"
    
    print("✅ Multiple deletions all persisted!")
