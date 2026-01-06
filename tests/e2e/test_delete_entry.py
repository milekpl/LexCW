import pytest
import time
import requests
from playwright.sync_api import Page, expect

# Assuming the Flask app is running on localhost:5000 for integration tests

@pytest.mark.integration
def test_delete_entry(page: Page, flask_test_server):  # type: ignore
    """
    Tests that an entry can be successfully deleted from the UI.
    """
    # Handle flask_test_server which now returns (base_url, project_id)
    if isinstance(flask_test_server, tuple):
        base_url = flask_test_server[0]
    else:
        base_url = flask_test_server

    # First, get an existing entry from the database to use for this test
    entries_response = requests.get(f"{base_url}/api/entries/?limit=1&offset=0")
    entries_data = entries_response.json()
    print(f"DEBUG: Available entries: {entries_data}")

    assert entries_data['total_count'] >= 1, "Test database should have at least one entry"
    entry_to_delete = entries_data['entries'][0]
    entry_id = entry_to_delete.get('id') or entry_to_delete.get('entry_id')
    lexical_unit_value = entry_to_delete.get('lexical_unit', {}).get('en', 'test')

    print(f"DEBUG: Will delete entry: {entry_id} ({lexical_unit_value})")

    # Now navigate to entries list
    page.goto(f"{base_url}/entries")
    expect(page).to_have_url(f"{base_url}/entries")

    # Force reload to bypass cache and wait for entries to load
    page.reload(wait_until="networkidle")

    # Wait for entries list to load
    page.wait_for_selector("#entries-list", state="visible", timeout=10000)
    page.wait_for_timeout(2000)  # Allow time for entries to populate

    # Filter entries so the entry is visible
    filter_input = page.locator("#filter-entries")
    filter_input.fill(lexical_unit_value)
    filter_btn = page.locator("#btn-filter")
    filter_btn.click()

    # Wait for filter to complete - wait for entry count to update from "Loading..."
    page.wait_for_function("""
        () => {
            const countEl = document.getElementById('entry-count');
            return countEl && !countEl.textContent.includes('Loading');
        }
    """, timeout=10000)

    # Debug output
    all_text = page.locator("#entries-list").text_content()
    print(f"DEBUG: Entries list content: {all_text[:300] if all_text else 'EMPTY'}")
    entry_count = page.locator("#entry-count").text_content()
    print(f"DEBUG: Entry count: {entry_count}")

    # Try to find the entry - use correct selector (entries-list IS the tbody, not a parent)
    entry_row = page.locator(f"#entries-list tr:has-text('{lexical_unit_value}')")

    expect(entry_row).to_be_visible(timeout=10000)
    delete_button = entry_row.locator("button.delete-btn")
    expect(delete_button).to_be_visible()

    # Click the delete button
    delete_button.click()

    # Confirm the deletion in the modal
    confirm_delete_button = page.locator("#confirm-delete")
    expect(confirm_delete_button).to_be_visible(timeout=5000)
    confirm_delete_button.click()

    # Verify success message
    expect(page.locator("text=Entry deleted successfully.")).to_be_visible(timeout=5000)

    # Verify that the entry is no longer present in the list
    expect(page.locator(f"text={entry_id}")).not_to_be_visible()
