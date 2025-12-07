import pytest
from playwright.sync_api import Page, expect

# Assuming the Flask app is running on localhost:5000 for integration tests

@pytest.mark.integration
def test_delete_entry(page: Page, flask_test_server):  # type: ignore
    """
    Tests that an entry can be successfully deleted from the UI.
    """
    # 1. Navigate to add entry page directly
    page.goto(f"{flask_test_server}/entries/add")
    
    # Wait for page to load
    page.wait_for_load_state("networkidle")
    page.wait_for_selector("input.lexical-unit-text", timeout=10000)
    
    # Fill in basic entry details
    lexical_unit_value = "TestEntryForDeletion"
    
    page.locator("input.lexical-unit-text").first.fill(lexical_unit_value)
    
    # Add a sense (check which button is visible)
    if page.locator("#add-first-sense-btn").is_visible():
        page.click("#add-first-sense-btn")
    else:
        page.click("#add-sense-btn")
    
    # Wait for sense to appear
    page.wait_for_selector(".sense-item", state="visible", timeout=5000)
    
    # Fill in definition
    sense_definition = page.locator(".sense-item .definition-text").first
    sense_definition.fill("A test definition for deletion.")
    
    # Submit the form
    page.click("button[type='submit']:has-text('Save Entry')")

    # After saving, extract the entry ID from the redirect URL
    # The URL should be /entries/<entry_id>?status=saved
    import re
    expect(page).not_to_have_url(f"{flask_test_server}/entries/add")
    current_url = page.url
    match = re.search(r"/entries/([\w\-]+)\?status=saved", current_url)
    assert match, f"Could not extract entry ID from URL: {current_url}"
    entry_id = match.group(1)
    expect(page.locator("text=Entry saved successfully.")).to_be_visible()

    # 3. Navigate back to the entries list
    page.goto(f"{flask_test_server}/entries")
    expect(page).to_have_url(f"{flask_test_server}/entries")

    # Filter entries so the newly created entry is visible
    page.fill("#filter-entries", lexical_unit_value)
    page.click("#btn-filter")

    # 4. Locate the delete button for the newly created entry
    # We need to find the row for the new entry and then its delete button
    entry_row = page.locator("#entries-list tr", has=page.locator(f"text={lexical_unit_value}"))
    expect(entry_row).to_be_visible()
    delete_button = entry_row.locator("button.delete-btn")
    expect(delete_button).to_be_visible()

    # 5. Click the delete button
    delete_button.click()

    # 6. Confirm the deletion in the modal
    confirm_delete_button = page.locator("#confirm-delete")
    expect(confirm_delete_button).to_be_visible()
    confirm_delete_button.click()

    # 7. Verify success message
    expect(page.locator("text=Entry deleted successfully.")).to_be_visible()

    # 8. Verify that the entry is no longer present in the list
    expect(page.locator(f"text={entry_id}")).not_to_be_visible()

    # Optional: Add a backend check if possible, but for UI integration, this is often sufficient.
    # For example, make an API call to verify it's gone from the database.
    # This would require a separate API client or a direct DB connection in the test setup.
