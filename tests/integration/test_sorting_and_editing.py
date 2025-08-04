#!/usr/bin/env python3
"""
Integration tests for date sorting and entry editing functionality.
Following TDD principles - tests written first to define expected behavior.
"""

import pytest
from playwright.sync_api import Page, expect
import time
import re


@pytest.mark.integration 
def test_date_modified_sorting_ascending(playwright_page: Page, live_server):
    """
    Test that sorting by 'Last Modified' in ascending order shows:
    1. Entries with dates first (oldest to newest)
    2. Entries without dates last (empty cells at bottom)
    
    This test verifies Issue #2 from TODO: "Sorting on Last Modified shows '–' at top"
    """
    # Navigate to entries list
    playwright_page.goto(f"{live_server.url}/entries")
    expect(playwright_page).to_have_url(f"{live_server.url}/entries")
    
    # Wait for entries to finish loading (dynamic content)
    playwright_page.wait_for_selector("tbody#entries-list tr[data-entry-id]", timeout=15000)
    
    # Wait for table headers to be rendered dynamically
    playwright_page.wait_for_selector("thead#entries-table-head th", timeout=10000)
    
    # Find and click the "Last Modified" column header to sort ascending
    last_modified_header = playwright_page.locator("th:has-text('Last Modified')")
    expect(last_modified_header).to_be_visible()
    last_modified_header.click()
    
    # Wait for sorting to complete
    time.sleep(3)
    playwright_page.wait_for_selector("tbody#entries-list tr[data-entry-id]", timeout=10000)
    
    # Get all date cells in the Last Modified column using the correct selector
    date_cells = playwright_page.locator("td[data-column-id='date_modified']")
    
    # Check that we have some entries
    expect(date_cells.first).to_be_visible()
    
    # Collect all visible date values
    date_values = []
    for i in range(min(25, date_cells.count())):  # Check first 25 entries to see empty ones
        cell_text = date_cells.nth(i).text_content()
        date_values.append(cell_text.strip())
    
    print(f"Date values in ascending order: {date_values}")
    
    # Verify sorting logic:
    # 1. Non-empty dates should come first
    # 2. Empty dates (whitespace, empty strings, or "–") should come last
    non_empty_dates = [d for d in date_values if d and d.strip() and d.strip() != "–"]
    empty_dates = [d for d in date_values if not d or not d.strip() or d.strip() == "–"]
    
    # All non-empty dates should appear before all empty dates
    non_empty_count = len(non_empty_dates)
    empty_count = len(empty_dates)
    
    print(f"Non-empty dates: {non_empty_count}, Empty dates: {empty_count}")
    print(f"Non-empty dates list: {non_empty_dates}")
    print(f"Empty dates list: {empty_dates}")
    
    # We need to have BOTH types to test sorting properly
    assert non_empty_count > 0, "Test data should have some entries with dates"
    assert empty_count > 0, "Test data should have some entries without dates for testing"
    
    # Verify that if we have both types, non-empty come first
    # The first non_empty_count values should be non-empty
    for i in range(non_empty_count):
        assert date_values[i] and date_values[i].strip() and date_values[i].strip() != "–", f"Expected non-empty date at position {i}, got: '{date_values[i]}'"
    
    # The remaining values should be empty
    for i in range(non_empty_count, len(date_values)):
        assert not date_values[i] or not date_values[i].strip() or date_values[i].strip() == "–", f"Expected empty date at position {i}, got: '{date_values[i]}'"


@pytest.mark.integration
def test_date_modified_sorting_descending(playwright_page: Page, live_server):
    """
    Test that sorting by 'Last Modified' in descending order shows:
    1. Entries with dates first (newest to oldest)  
    2. Entries without dates last (empty cells at bottom)
    """
    # Navigate to entries list
    playwright_page.goto(f"{live_server.url}/entries")
    expect(playwright_page).to_have_url(f"{live_server.url}/entries")
    
    # Wait for entries to load
    playwright_page.wait_for_selector("table tbody tr", timeout=10000)
    
    # Find and click the "Last Modified" column header twice to sort descending
    last_modified_header = playwright_page.locator("th:has-text('Last Modified')")
    expect(last_modified_header).to_be_visible()
    last_modified_header.click()  # First click - ascending
    time.sleep(1)
    last_modified_header.click()  # Second click - descending
    
    # Wait for sorting to complete
    time.sleep(2)
    
    # Get all date cells in the Last Modified column  
    date_cells = playwright_page.locator("tbody tr td:nth-child(6)")
    
    # Check that we have some entries
    expect(date_cells.first).to_be_visible()
    
    # Collect all visible date values
    date_values = []
    for i in range(min(10, date_cells.count())):
        cell_text = date_cells.nth(i).text_content()
        date_values.append(cell_text.strip())
    
    print(f"Date values in descending order: {date_values}")
    
    # Verify descending sort: newest dates first, empty dates last
    non_empty_dates = [d for d in date_values if d and d.strip()]
    empty_dates = [d for d in date_values if not d or not d.strip()]
    
    non_empty_count = len(non_empty_dates)
    empty_count = len(empty_dates)
    
    print(f"Non-empty dates: {non_empty_count}, Empty dates: {empty_count}")
    
    # Verify that if we have both types, non-empty come first
    if non_empty_count > 0 and empty_count > 0:
        # The first non_empty_count values should be non-empty
        for i in range(non_empty_count):
            assert date_values[i] and date_values[i].strip(), f"Expected non-empty date at position {i}, got: '{date_values[i]}'"
        
        # The remaining values should be empty  
        for i in range(non_empty_count, len(date_values)):
            assert not date_values[i] or not date_values[i].strip(), f"Expected empty date at position {i}, got: '{date_values[i]}'"


@pytest.mark.integration
def test_entry_editing_loads_successfully(playwright_page: Page, live_server):
    """
    Test that clicking "Edit" on an entry successfully loads the edit form.
    
    This verifies the regression: "Error loading entry: 'list' object has no attribute 'get'"
    """
    # Navigate to entries list
    playwright_page.goto(f"{live_server.url}/entries")
    expect(playwright_page).to_have_url(f"{live_server.url}/entries")
    
    # Wait for entries to load
    playwright_page.wait_for_selector("table tbody tr", timeout=10000)
    
    # Find the first entry with an edit button
    first_edit_button = playwright_page.locator("tbody tr .edit-btn").first
    expect(first_edit_button).to_be_visible()
    
    # Get the entry ID from the edit button's href attribute
    edit_href = first_edit_button.get_attribute("href")
    assert edit_href, "Edit button should have href attribute"
    
    # Extract entry ID from href like "/entries/some-id/edit"
    entry_id_match = re.search(r"/entries/([^/]+)/edit", edit_href)
    assert entry_id_match, f"Could not extract entry ID from href: {edit_href}"
    entry_id = entry_id_match.group(1)
    
    print(f"Testing edit for entry ID: {entry_id}")
    
    # Click the edit button
    first_edit_button.click()
    
    # Verify we navigated to the edit page
    expected_url = f"{live_server.url}/entries/{entry_id}/edit"
    # URL encode the expected URL to match browser behavior
    from urllib.parse import quote
    expected_url_encoded = f"{live_server.url}/entries/{quote(entry_id)}/edit"
    
    # Check if current URL matches either the unencoded or encoded version
    current_url = playwright_page.url
    if current_url == expected_url or current_url == expected_url_encoded:
        # Success - edit page loaded
        pass
    else:
        # If URL doesn't match, fail with descriptive message
        assert False, f"Expected edit page URL, got: {current_url}"
    
    # Verify the edit form loaded successfully (no error message)
    # Check for common error indicators
    error_alert = playwright_page.locator(".alert-danger, .error, [class*='error']")
    expect(error_alert).not_to_be_visible()
    
    # Verify form elements are present
    lexical_unit_field = playwright_page.locator("#lexical-unit")
    expect(lexical_unit_field).to_be_visible()
    
    # Verify the form has the entry data loaded (not empty)
    lexical_unit_value = lexical_unit_field.input_value()
    assert lexical_unit_value.strip(), "Lexical unit field should not be empty in edit mode"
    
    print(f"Edit form loaded successfully with lexical unit: {lexical_unit_value}")


@pytest.mark.integration  
def test_entry_editing_save_functionality(playwright_page: Page, live_server):
    """
    Test that editing an entry and saving it works without errors.
    
    This is a comprehensive test of the edit workflow.
    """
    # Navigate to entries list
    playwright_page.goto(f"{live_server.url}/entries")
    expect(playwright_page).to_have_url(f"{live_server.url}/entries")
    
    # Wait for entries to load
    playwright_page.wait_for_selector("table tbody tr", timeout=10000)
    
    # Find the first entry with an edit button
    first_edit_button = playwright_page.locator("tbody tr .edit-btn").first
    expect(first_edit_button).to_be_visible()
    
    # Click the edit button
    first_edit_button.click()
    
    # Wait for edit form to load
    playwright_page.wait_for_selector("#lexical-unit", timeout=10000)
    
    # Get original value
    lexical_unit_field = playwright_page.locator("#lexical-unit")
    original_value = lexical_unit_field.input_value()
    
    # Make a small change (add timestamp)
    test_suffix = f" [edited-{int(time.time())}]"
    new_value = original_value + test_suffix
    
    # Clear and fill with new value
    lexical_unit_field.fill(new_value)
    
    # Find and click save button
    save_button = playwright_page.locator("button[type='submit']:has-text('Save Entry'), button:has-text('Save')")
    expect(save_button).to_be_visible()
    save_button.click()
    
    # Wait for save to complete and redirect
    # Should redirect to entry view with success message
    playwright_page.wait_for_url(re.compile(r"/entries/[^/]+(\?.*)?$"), timeout=10000)
    
    # Check for success message
    success_message = playwright_page.locator(".alert-success, .success, [class*='success']")
    expect(success_message).to_be_visible(timeout=5000)
    
    # Verify the change was saved by checking the displayed value
    displayed_lexical_unit = playwright_page.locator("h1, .lexical-unit, [class*='lexical']").first
    expect(displayed_lexical_unit).to_contain_text(test_suffix)
    
    print(f"Entry successfully edited and saved with new value: {new_value}")


@pytest.mark.integration
def test_multiple_entries_sorting_consistency(playwright_page: Page, live_server):
    """
    Test that sorting works consistently across multiple clicks and doesn't break.
    """
    # Navigate to entries list
    playwright_page.goto(f"{live_server.url}/entries")
    expect(playwright_page).to_have_url(f"{live_server.url}/entries")
    
    # Wait for entries to load
    playwright_page.wait_for_selector("table tbody tr", timeout=10000)
    
    last_modified_header = playwright_page.locator("th:has-text('Last Modified')")
    expect(last_modified_header).to_be_visible()
    
    # Test multiple sorting operations
    for i in range(3):
        print(f"Sort operation {i+1}")
        
        # Click to sort
        last_modified_header.click()
        time.sleep(2)
        
        # Verify table still has data
        rows = playwright_page.locator("tbody tr")
        expect(rows.first).to_be_visible()
        
        # Verify no error messages appeared
        error_alert = playwright_page.locator(".alert-danger, .error")
        expect(error_alert).not_to_be_visible()
        
    print("Multiple sorting operations completed successfully")
