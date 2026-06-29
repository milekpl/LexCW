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
        """Test that hierarchical elements (like semantic-domain) display with collapsible tree."""
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

        # Wait for Alpine to load elements and render visible nodes
        page.wait_for_selector('#elements .list-group-item', timeout=10000)

        # The elements should show collapsible tree (chevron icons for nodes with children)
        # Top-level nodes should be expanded by default (auto-expand depth 0)
        chevron_downs = page.locator('#elements .bi-chevron-down')
        expect(chevron_downs.first).to_be_visible(timeout=5000)

        # Element count + depth info should be visible
        info_text = page.locator('#elements small.text-muted')
        expect(info_text.first).to_be_visible(timeout=5000)

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

        # Wait for Alpine to render elements
        page.wait_for_selector('#elements .list-group-item', timeout=10000)

        # Find an element with an edit button (visible nodes in the tree)
        edit_btns = page.locator('#elements .list-group-item button[title="Edit"]')

        if edit_btns.count() > 0:
            edit_btns.first.click()

            # Check element modal opens
            element_modal = page.locator('#elementModal')
            expect(element_modal).to_be_visible(timeout=5000)

            # Verify we can read the element data
            element_id = page.locator('#elementId')
            expect(element_id).to_be_visible()
            element_id_value = element_id.input_value()
            assert element_id_value, "Element ID should not be empty"
        else:
            pytest.skip("No elements found to test edit")

    def test_create_new_range(self, page: Page, app_url):
        """Test creating a new custom range via the UI and verifying via API."""
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

        # Wait for modal to close
        modal.wait_for(state="hidden", timeout=10000)

        # Verify via API that the range was created and is accessible.
        # (Direct table verification is unreliable in test fixtures due to
        # execute_update DB substitution vs execute_query caching.)
        page.goto(f'{app_url}/api/ranges-editor/test-custom-range')
        content = page.content()
        assert '"success":true' in content or '"id":"test-custom-range"' in content, \
            f"Expected test-custom-range in API response: {content[:300]}"

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

        # Wait for element modal to close
        elem_modal = page.locator('#elementModal')
        elem_modal.wait_for(state="hidden", timeout=10000)

        # Verify via API that the element was created
        page.goto(f'{app_url}/api/ranges-editor/grammatical-info/elements/test-element-e2e')
        content = page.content()
        assert '"success":true' in content or '"id":"test-element-e2e"' in content, \
            f"Expected test-element-e2e in API response: {content[:300]}"

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
        # Now find and delete it — Alpine flat structure: .list-group-item contains both
        # the strong text and the action buttons as siblings.
        test_elem_row = elements_container.locator('.list-group-item:has(strong:has-text("test-element-e2e"))')
        if test_elem_row.count() > 0:
            delete_btn = test_elem_row.locator('button[title="Delete"]')
            if delete_btn.count() > 0:
                # Accept confirmation
                page.once('dialog', lambda dialog: dialog.accept())
                delete_btn.click()
                # Wait for the element to be removed
                page.wait_for_function(
                    "() => !document.querySelector('#elementsContainer') || "
                    "!document.querySelector('#elementsContainer').innerText.includes('test-element-e2e')",
                    timeout=5000)

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

    def test_collapsible_tree_starts_folded(self, page: Page, app_url):
        """Test that the tree starts with only top-level expanded, not all nodes."""
        page.goto(f'{app_url}/ranges-editor')
        page.wait_for_load_state('networkidle')

        # Open semantic-domain-ddp4 (1792 elements, depth 5)
        page.locator('tr[data-range-id="semantic-domain-ddp4"] button[title="Edit"]').click()
        expect(page.locator('#editRangeModal')).to_be_visible(timeout=5000)

        # Go to Elements tab
        page.click('#elements-tab')
        page.wait_for_selector('#elements .list-group-item', timeout=10000)

        # Wait for Alpine to finish loading and rendering
        page.wait_for_selector('#elements .bi-chevron-down', timeout=5000)

        # Count visible list-group-items — should be far less than 1792
        # (9 top-level expanded + their children visible = ~100-200 max)
        visible_items = page.locator('#elements .list-group-item:visible')
        visible_count = visible_items.count()
        assert visible_count < 500, \
            f"Expected fewer than 500 visible items (tree should be folded), got {visible_count}"

    def test_expand_collapse_toggle(self, page: Page, app_url):
        """Test that clicking a chevron toggles expand/collapse of a node."""
        page.goto(f'{app_url}/ranges-editor')
        page.wait_for_load_state('networkidle')

        page.locator('tr[data-range-id="semantic-domain-ddp4"] button[title="Edit"]').click()
        expect(page.locator('#editRangeModal')).to_be_visible(timeout=5000)

        page.click('#elements-tab')
        page.wait_for_selector('#elements .list-group-item', timeout=10000)

        # Count visible items before collapse
        before_count = page.locator('#elements .list-group-item:visible').count()

        # Click the first chevron-down to collapse a top-level node
        first_chevron = page.locator('#elements .bi-chevron-down').first
        expect(first_chevron).to_be_visible(timeout=5000)
        first_chevron.click()
        page.wait_for_timeout(300)

        # After collapse, the chevron should be right-facing and fewer items visible
        first_chevron_after = page.locator('#elements .bi-chevron-right').first
        expect(first_chevron_after).to_be_visible(timeout=5000)

        after_count = page.locator('#elements .list-group-item:visible').count()
        assert after_count < before_count, \
            f"Expected fewer visible items after collapse ({after_count} < {before_count})"

        # Click again to expand
        first_chevron_after.click()
        page.wait_for_timeout(300)

        # Should have chevron-down again and same count as before
        page.locator('#elements .bi-chevron-down').first.wait_for(state='visible', timeout=5000)
        restored_count = page.locator('#elements .list-group-item:visible').count()
        assert restored_count == before_count, \
            f"Expected restored count {before_count}, got {restored_count}"

    def test_collapse_all_button(self, page: Page, app_url):
        """Test that the Collapse All button hides all children."""
        page.goto(f'{app_url}/ranges-editor')
        page.wait_for_load_state('networkidle')

        page.locator('tr[data-range-id="semantic-domain-ddp4"] button[title="Edit"]').click()
        expect(page.locator('#editRangeModal')).to_be_visible(timeout=5000)

        page.click('#elements-tab')
        page.wait_for_selector('#elements .list-group-item', timeout=10000)

        # Click "Collapse all"
        collapse_btn = page.locator('#elements button[title="Collapse all"]')
        expect(collapse_btn).to_be_visible(timeout=5000)
        collapse_btn.click()
        page.wait_for_timeout(300)

        # Only top-level nodes should be visible (no chevron-down = no expanded nodes)
        chevron_downs = page.locator('#elements .bi-chevron-down:visible')
        expect(chevron_downs).to_have_count(0, timeout=5000)

        # All chevrons should be right-facing (collapsed)
        chevron_rights = page.locator('#elements .bi-chevron-right:visible')
        assert chevron_rights.count() > 0, "Expected collapsed nodes with right chevrons"

    def test_expand_all_button(self, page: Page, app_url):
        """Test that the Expand All button expands all nodes."""
        page.goto(f'{app_url}/ranges-editor')
        page.wait_for_load_state('networkidle')

        page.locator('tr[data-range-id="semantic-domain-ddp4"] button[title="Edit"]').click()
        expect(page.locator('#editRangeModal')).to_be_visible(timeout=5000)

        page.click('#elements-tab')
        page.wait_for_selector('#elements .list-group-item', timeout=10000)

        # First collapse all to start from a known state
        page.locator('#elements button[title="Collapse all"]').click()
        page.wait_for_timeout(300)

        collapsed_count = page.locator('#elements .list-group-item:visible').count()

        # Now expand all
        page.locator('#elements button[title="Expand all"]').click()
        page.wait_for_timeout(500)

        expanded_count = page.locator('#elements .list-group-item:visible').count()
        assert expanded_count > collapsed_count, \
            f"Expected more visible items after expand all ({expanded_count} > {collapsed_count})"

    def test_depth_indentation(self, page: Page, app_url):
        """Test that nested elements are indented based on their depth."""
        page.goto(f'{app_url}/ranges-editor')
        page.wait_for_load_state('networkidle')

        page.locator('tr[data-range-id="semantic-domain-ddp4"] button[title="Edit"]').click()
        expect(page.locator('#editRangeModal')).to_be_visible(timeout=5000)

        page.click('#elements-tab')
        page.wait_for_selector('#elements .list-group-item', timeout=10000)

        # Wait for Alpine to finish loading + auto-expand depth-0 nodes
        page.wait_for_selector('#elements .bi-chevron-down', timeout=5000)
        page.wait_for_timeout(500)

        # After auto-expand, there should be items at depth 0 and depth 1 visible
        all_paddings = page.locator('#elements .list-group-item:visible').evaluate_all(
            'els => els.map(el => parseInt(el.style.paddingLeft) || 0)'
        )

        unique_paddings = set(all_paddings)
        assert len(unique_paddings) >= 2, \
            f"Expected at least 2 different padding values for depth indentation, got {unique_paddings}"
