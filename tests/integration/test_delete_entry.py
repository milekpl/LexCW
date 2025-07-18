import pytest
from playwright.sync_api import Page, expect

# Assuming the Flask app is running on localhost:5000 for integration tests

@pytest.mark.integration
def test_delete_entry(playwright_page: Page, live_server):  # type: ignore
    """
    Tests that an entry can be successfully deleted from the UI.
    """
    # 1. Navigate to the entries list page
    playwright_page.goto(f"{live_server.url}/entries")

    # 2. Add a new entry to ensure we have something to delete
    # This assumes the "Add New Entry" button and form work.
    # In a real scenario, you might use a fixture to pre-populate the DB.
    playwright_page.click("text=Add New Entry")
    expect(playwright_page).to_have_url(f"{live_server.url}/entries/add")

    # Fill in basic entry details
    playwright_page.fill("#lexical-unit", "TestEntryForDeletion")
    playwright_page.click("#add-sense-btn") # Add a sense to make it valid
    playwright_page.fill("textarea[name*='definition']", "A test definition for deletion.")
    playwright_page.click("button[type='submit']:has-text('Save Entry')")

    # Verify successful save and redirection to the entry view page
    expect(playwright_page).to_have_url(f"{live_server.url}/entries/TestEntryForDeletion?status=saved")
    expect(playwright_page.locator("text=Entry saved successfully.")).to_be_visible()

    # 3. Navigate back to the entries list
    playwright_page.goto(f"{live_server.url}/entries")
    expect(playwright_page).to_have_url(f"{live_server.url}/entries")

    # 4. Locate the delete button for the newly created entry
    # We need to find the row for "TestEntryForDeletion" and then its delete button
    entry_row = playwright_page.locator("tr", has=playwright_page.locator("text=TestEntryForDeletion"))
    delete_button = entry_row.locator("button.delete-btn")
    expect(delete_button).to_be_visible()

    # 5. Click the delete button
    delete_button.click()

    # 6. Confirm the deletion in the modal
    confirm_delete_button = playwright_page.locator("#confirm-delete")
    expect(confirm_delete_button).to_be_visible()
    confirm_delete_button.click()

    # 7. Verify success message
    expect(playwright_page.locator("text=Entry deleted successfully.")).to_be_visible()

    # 8. Verify that the entry is no longer present in the list
    expect(playwright_page.locator("text=TestEntryForDeletion")).not_to_be_visible()

    # Optional: Add a backend check if possible, but for UI integration, this is often sufficient.
    # For example, make an API call to verify it's gone from the database.
    # This would require a separate API client or a direct DB connection in the test setup.
