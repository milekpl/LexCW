import pytest
import time
import requests
from playwright.sync_api import Page, expect

# Assuming the Flask app is running on localhost:5000 for integration tests

@pytest.mark.integration
def test_delete_entry(page: Page, flask_test_server):  # type: ignore
    """
    Tests that an entry can be successfully deleted from the UI.
    This test creates its own entry to ensure isolation.
    """
    # Handle flask_test_server which now returns (base_url, project_id)
    if isinstance(flask_test_server, tuple):
        base_url = flask_test_server[0]
    else:
        base_url = flask_test_server

    # First, create a test entry via API to ensure we have one to delete
    # This ensures test isolation - we don't depend on other tests to create entries
    test_entry_data = {
        "id": "entry_to_delete_" + str(hash(str(time.time())))[-8:],
        "lexical_unit": {"en": "deleteme"},
        "senses": [
            {
                "id": "sense_1",
                "definition": {"en": "A test sense for deletion"},
                "gloss": {"en": "delete"}
            }
        ]
    }

    create_response = requests.post(
        f"{base_url}/api/entries/",
        json=test_entry_data,
        headers={"Content-Type": "application/json"}
    )
    assert create_response.status_code in [200, 201], f"Failed to create test entry: {create_response.text}"

    entry_id = test_entry_data["id"]
    lexical_unit_value = "deleteme"

    print(f"DEBUG: Created entry to delete: {entry_id}")

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

    # Verify via API that entry is actually deleted
    get_response = requests.get(f"{base_url}/api/entries/{entry_id}")
    assert get_response.status_code == 404, f"Entry {entry_id} should have been deleted"
