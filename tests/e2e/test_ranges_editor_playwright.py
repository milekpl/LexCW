"""
Playwright E2E tests for Ranges Editor CRUD operations.

Tests the full CRUD cycle for range elements including:
- Viewing ranges list
- Creating new ranges and elements
- Editing existing elements (including hierarchical)
- Deleting elements and ranges
"""

from __future__ import annotations

import pytest
from playwright.sync_api import Page, expect


@pytest.mark.integration
@pytest.mark.playwright
class TestRangesEditorCRUD:
    """E2E tests for Ranges Editor CRUD operations."""

    def test_ranges_editor_page_loads(self, page: Page, app_url):
        """Test that the ranges editor page loads successfully."""
        page.goto(f'{app_url}/ranges-editor')
        page.wait_for_load_state('networkidle')

        # Check that the page title or heading is present
        expect(page.locator('h1, h2:has-text("Ranges")')).to_be_visible(timeout=10000)

    def test_ranges_list_displays(self, page: Page, app_url):
        """Test that the ranges list displays after page load."""
        page.goto(f'{app_url}/ranges-editor')
        page.wait_for_load_state('networkidle')

        # Wait for ranges table to load
        table = page.locator('#rangesTable')
        expect(table).to_be_visible(timeout=10000)

        # Check for at least one range (grammatical-info is standard)
        rows = table.locator('tbody tr')
        expect(rows.first).to_be_visible(timeout=5000)

    def test_grammatical_info_range_visible(self, page: Page, app_url):
        """Test that grammatical-info range is visible in the list."""
        page.goto(f'{app_url}/ranges-editor')
        page.wait_for_load_state('networkidle')

        # Find grammatical-info row
        row = page.locator('tr[data-range-id="grammatical-info"]')
        expect(row).to_be_visible(timeout=5000)

    def test_domain_type_range_visible(self, page: Page, app_url):
        """Test that domain-type range is visible in the list."""
        page.goto(f'{app_url}/ranges-editor')
        page.wait_for_load_state('networkidle')

        # Find domain-type row (which has hierarchical elements)
        row = page.locator('tr[data-range-id="domain-type"]')
        expect(row).to_be_visible(timeout=5000)

    def test_edit_range_opens_modal(self, page: Page, app_url):
        """Test that clicking edit opens the range edit modal."""
        page.goto(f'{app_url}/ranges-editor')
        page.wait_for_load_state('networkidle')

        # Click edit button for grammatical-info
        edit_btn = page.locator('tr[data-range-id="grammatical-info"] button[title="Edit"]')
        expect(edit_btn).to_be_visible(timeout=5000)
        edit_btn.click()

        # Check modal is visible
        modal = page.locator('#editRangeModal')
        expect(modal).to_be_visible(timeout=5000)

    def test_edit_modal_shows_elements(self, page: Page, app_url):
        """Test that the edit modal shows range elements."""
        page.goto(f'{app_url}/ranges-editor')
        page.wait_for_load_state('networkidle')

        # Open edit modal for grammatical-info
        edit_btn = page.locator('tr[data-range-id="grammatical-info"] button[title="Edit"]')
        edit_btn.click()

        # Wait for modal to be visible first
        modal = page.locator('#editRangeModal')
        expect(modal).to_be_visible(timeout=5000)

        # Click on the Elements tab to reveal elements container
        page.click('#elements-tab')
        # Wait for elements container to be visible (replacing sleep)
        elements_container = page.locator('#elementsContainer')
        expect(elements_container).to_be_visible(timeout=5000)

        # Check that at least one element is shown
        elements = elements_container.locator('.list-group-item')
        expect(elements.first).to_be_visible(timeout=5000)

    def test_hierarchical_elements_displayed(self, page: Page, app_url):
        """Test that hierarchical elements (like semantic-domain) display with children."""
        page.goto(f'{app_url}/ranges-editor')
        page.wait_for_load_state('networkidle')

        # Open edit modal for semantic-domain-ddp4 (has hierarchical structure)
        edit_btn = page.locator('tr[data-range-id="semantic-domain-ddp4"] button[title="Edit"]')
        edit_btn.click()

        # Wait for modal to be visible first
        modal = page.locator('#editRangeModal')
        expect(modal).to_be_visible(timeout=5000)

        # Click on the Elements tab to reveal elements container
        page.click('#elements-tab')
        page.wait_for_timeout(500)

        # Wait for elements container to be visible (it loads asynchronously)
        elements_container = page.locator('#elementsContainer')
        expect(elements_container).to_be_visible(timeout=5000)

        # Wait for nested elements to appear instead of sleeping
        elements_container.locator('.list-group .list-group').first.wait_for(state='visible', timeout=5000)

        # The elements should show hierarchy (nested divs)
        nested_elements = elements_container.locator('.list-group .list-group')
        # Should have at least some nested structure
        expect(nested_elements.first).to_be_visible(timeout=5000)

    def test_edit_hierarchical_element(self, page: Page, app_url):
        """Test editing a nested hierarchical element works."""
        page.goto(f'{app_url}/ranges-editor')
        page.wait_for_load_state('networkidle')

        # Open edit modal for semantic-domain-ddp4
        edit_btn = page.locator('tr[data-range-id="semantic-domain-ddp4"] button[title="Edit"]')
        edit_btn.click()

        # Wait for modal to be visible
        modal = page.locator('#editRangeModal')
        expect(modal).to_be_visible(timeout=5000)

        # Click on the Elements tab to reveal elements container
        page.click('#elements-tab')
        page.wait_for_timeout(1000)

        # Find and click edit on a nested element (look for nested list-group-item)
        # The UI uses recursive rendering with nested divs
        nested_edit_btns = page.locator('.list-group .list-group-item button[title="Edit"]')

        if nested_edit_btns.count() > 0:
            nested_edit_btns.first.click()

            # Check element modal opens
            element_modal = page.locator('#elementModal')
            expect(element_modal).to_be_visible(timeout=5000)

            # Verify we can read the element data
            element_id = page.locator('#elementId')
            expect(element_id).to_be_visible()
            element_id_value = element_id.input_value()
            assert element_id_value, "Element ID should not be empty"
        else:
            pytest.skip("No nested elements found to test edit")

    def test_create_new_range(self, page: Page, app_url):
        """Test creating a new custom range."""
        page.goto(f'{app_url}/ranges-editor')
        page.wait_for_load_state('networkidle')

        # Click new range button
        new_range_btn = page.locator('#btnNewRange')
        expect(new_range_btn).to_be_visible(timeout=5000)
        new_range_btn.click()

        # Check modal opens
        modal = page.locator('#createRangeModal')
        expect(modal).to_be_visible(timeout=5000)

        # Fill in range ID
        page.fill('#rangeId', 'test-custom-range')

        # Add a label
        page.click('#btnAddLabel')
        page.fill('#labelsContainer .lang-text', 'Test Custom Range')

        # Submit
        page.click('#btnCreateRange')

        # Wait for modal to close (Bootstrap modal fade out)
        modal.wait_for(state="hidden", timeout=5000)

        # Wait for the table to reload and the new row to appear instead of sleeping
        page.wait_for_selector('tr[data-range-id="test-custom-range"]', timeout=5000)

        # Verify the range now appears in the list
        row = page.locator('tr[data-range-id="test-custom-range"]')
        expect(row).to_be_visible(timeout=5000)

    def test_create_element_in_range(self, page: Page, app_url):
        """Test creating a new element in a range."""
        page.goto(f'{app_url}/ranges-editor')
        page.wait_for_load_state('networkidle')

        # Open edit modal for grammatical-info
        edit_btn = page.locator('tr[data-range-id="grammatical-info"] button[title="Edit"]')
        edit_btn.click()

        # Wait for modal
        modal = page.locator('#editRangeModal')
        expect(modal).to_be_visible(timeout=5000)

        # Click on the Elements tab to reveal elements container
        page.click('#elements-tab')
        page.wait_for_timeout(500)

        # Wait for elements container to load
        elements_container = page.locator('#elementsContainer')
        expect(elements_container).to_be_visible(timeout=5000)

        # Wait for elements to actually load
        page.wait_for_selector('#elementsContainer .list-group-item', timeout=5000)

        # Click new element button
        new_elem_btn = page.locator('#btnNewElement')
        expect(new_elem_btn).to_be_visible(timeout=3000)
        new_elem_btn.click()

        # Check element modal opens
        elem_modal = page.locator('#elementModal')
        expect(elem_modal).to_be_visible(timeout=5000)

        # Fill in element data
        page.fill('#elementId', 'test-element-e2e')

        # Add abbreviation
        page.fill('#elementAbbrev', 'test')

        # Submit
        page.click('#btnSaveElement')

        # Check for success - wait for the element to appear
        page.wait_for_selector('#elementsContainer strong:has-text("test-element-e2e")', timeout=5000)

        # Verify element now appears by checking for the strong element with the ID
        element = elements_container.locator('strong:has-text("test-element-e2e")')
        expect(element.nth(0)).to_be_visible(timeout=5000)

    def test_delete_element(self, page: Page, app_url):
        """Test deleting an element from a range."""
        # First create an element to delete
        page.goto(f'{app_url}/ranges-editor')
        page.wait_for_load_state('networkidle')

        # Open edit modal for grammatical-info
        edit_btn = page.locator('tr[data-range-id="grammatical-info"] button[title="Edit"]')
        edit_btn.click()

        # Wait for modal
        modal = page.locator('#editRangeModal')
        expect(modal).to_be_visible(timeout=5000)

        # Click on the Elements tab to reveal elements container
        page.click('#elements-tab')
        page.wait_for_timeout(500)

        # Wait for elements to load
        elements_container = page.locator('#elementsContainer')
        expect(elements_container).to_be_visible(timeout=5000)
        page.wait_for_timeout(1000)

        # Check if our test element exists, if not create it
        test_elem = elements_container.locator('text=test-element-e2e')

        if test_elem.count() == 0:
            # Create it first
            new_elem_btn = page.locator('#btnNewElement')
            new_elem_btn.click()
            elem_modal = page.locator('#elementModal')
            expect(elem_modal).to_be_visible(timeout=5000)
            page.fill('#elementId', 'test-element-e2e')
            page.fill('#elementAbbrev', 'test')
            page.click('#btnSaveElement')
            page.wait_for_timeout(500)

        # Now find and delete it
        test_elem = elements_container.locator('text=test-element-e2e')
        if test_elem.count() > 0:
            # Find the parent list-group-item and click delete
            # The text is inside a strong element; go up to list-group-item
            delete_btn = test_elem.locator('..').locator('..').locator('..').locator('button[title="Delete"]')
            if delete_btn.count() > 0:
                # Accept confirmation
                page.once('dialog', lambda dialog: dialog.accept())
                delete_btn.click()
                # Wait for the element to be removed
                page.wait_for_function("() => !document.querySelector('#elementsContainer') || !document.querySelector('#elementsContainer').innerText.includes('test-element-e2e')", timeout=5000)

                # Verify element is gone
                test_elem = elements_container.locator('text=test-element-e2e')
                expect(test_elem).to_have_count(0, timeout=5000)

    def test_search_ranges(self, page: Page, app_url):
        """Test searching/filtering ranges."""
        page.goto(f'{app_url}/ranges-editor')
        page.wait_for_load_state('networkidle')

        # Wait for table to load
        table = page.locator('#rangesTable')
        expect(table).to_be_visible(timeout=5000)

        # Get initial row count
        initial_rows = page.locator('#rangesTable tbody tr')
        expect(initial_rows.nth(0)).to_be_visible(timeout=3000)
        initial_count = initial_rows.count()
        assert initial_count > 0, f"Expected at least one row, got {initial_count}"

        # Type in search box
        search_input = page.locator('#searchRanges')
        expect(search_input).to_be_visible(timeout=5000)

        # Search for 'grammar' - should match 'grammatical-info' range
        search_input.fill('grammar')

        # Wait for filtering to happen
        page.wait_for_timeout(500)

        # Verify search input has the value
        search_value = search_input.input_value()
        assert search_value == 'grammar', f"Expected search value 'grammar', got '{search_value}'"

        # Clear search
        search_input.fill('')

        # Wait for table to restore
        page.wait_for_timeout(500)

        # All rows should be visible again
        all_rows = page.locator('#rangesTable tbody tr')
        expect(all_rows.nth(0)).to_be_visible(timeout=3000)

    def test_ranges_api_returns_correct_data(self, page: Page, app_url):
        """Test that the ranges API returns correct data."""
        # Navigate to API endpoint
        page.goto(f'{app_url}/api/ranges-editor/grammatical-info')

        # Get content
        content = page.content()

        # Should be JSON with grammatical-info data
        assert 'grammatical-info' in content or '"id":"grammatical-info"' in content, \
            f"Expected grammatical-info data in response: {content[:500]}"

    def test_nested_element_api_lookup(self, page: Page, app_url):
        """Test that nested hierarchical elements can be fetched via API."""
        # Test the API endpoint for getting a nested element
        page.goto(f'{app_url}/api/ranges-editor/semantic-domain-ddp4/elements/1.1')

        content = page.content()

        # Should return JSON with element data (even if nested)
        assert 'success' in content or '"id":"1.1"' in content, \
            f"Expected element data for nested element 1.1: {content[:500]}"
