import pytest
from playwright.sync_api import Page, expect

# Assuming the Flask app is running on localhost:5000 for integration tests

@pytest.mark.integration
def test_delete_entry(page: Page, flask_test_server):  # type: ignore
    """
    Tests that an entry can be successfully deleted from the UI.
    """
    # Instead of relying on complex form submission, create entry via API
    import requests
    import uuid
    
    # Generate unique entry ID
    entry_id = f"test_entry_delete_{uuid.uuid4().hex[:8]}"
    lexical_unit_value = "TestEntryForDeletion"
    
    # Create entry via API using LIFT XML (just the entry element, not full document)
    lift_xml = f'''<entry xmlns="http://fieldworks.sil.org/schemas/lift/0.13" id="{entry_id}" dateCreated="2024-12-07T10:00:00Z" dateModified="2024-12-07T10:00:00Z">
  <lexical-unit>
    <form lang="en"><text>{lexical_unit_value}</text></form>
  </lexical-unit>
  <sense id="{entry_id}_sense1" order="0">
    <definition>
      <form lang="en"><text>A test definition for deletion.</text></form>
    </definition>
  </sense>
</entry>'''
    
    # Create entry via XML API
    response = requests.post(
        f"{flask_test_server}/api/xml/entries",
        data=lift_xml.encode('utf-8'),
        headers={'Content-Type': 'application/xml'}
    )
    
    assert response.status_code == 201, f"Failed to create entry: {response.text}"
    print(f"DEBUG: Created entry with ID: {entry_id}")
    
    # Verify entry was created by checking via API
    verify_response = requests.get(f"{flask_test_server}/api/entries/{entry_id}")
    print(f"DEBUG: Entry verification status: {verify_response.status_code}")
    if verify_response.status_code == 200:
        print(f"DEBUG: Entry exists in database")
    else:
        print(f"DEBUG: Entry NOT found: {verify_response.text}")
    
    # Small delay to allow database to update
    import time
    time.sleep(1)

    # Now navigate to entries list and delete it
    page.goto(f"{flask_test_server}/entries")
    expect(page).to_have_url(f"{flask_test_server}/entries")
    
    # Force reload to bypass cache
    page.reload(wait_until="networkidle")
    
    # Wait for entries list to load
    page.wait_for_selector("#entries-list", state="visible", timeout=5000)
    page.wait_for_timeout(2000)  # Allow time for entries to populate

    # Filter entries so the newly created entry is visible
    filter_input = page.locator("#filter-entries")
    filter_input.fill(lexical_unit_value)
    filter_btn = page.locator("#btn-filter")
    filter_btn.click()
    
    # Wait for filter to complete
    page.wait_for_timeout(2000)  # Increased wait time for filter
    
    # Try to find the entry - use correct selector (entries-list IS the tbody, not a parent)
    entry_row = page.locator(f"#entries-list tr:has-text('{lexical_unit_value}')")
    
    # Debug output
    all_text = page.locator("#entries-list").text_content()
    print(f"DEBUG: Entries list content: {all_text[:200] if all_text else 'EMPTY'}")
    
    expect(entry_row).to_be_visible(timeout=5000)
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
