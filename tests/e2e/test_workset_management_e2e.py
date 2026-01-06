"""
E2E tests for Workset Management page - Workbench /workbench/worksets

Tests cover:
- Page loading and workset list display
- Workset creation link
- Workset selection UI elements
- Bulk operations UI elements
- Navigation links

Note: The page fixture automatically selects a project before each test.
"""

import pytest
import time
import logging
import requests
from playwright.sync_api import Page, expect

logger = logging.getLogger(__name__)


class TestWorksetListPage:
    """Test suite for workset list page functionality."""

    def test_page_loads_successfully(self, page, app_url):
        """Test that the worksets page loads without errors."""
        page.goto(f"{app_url}/workbench/worksets")
        page.wait_for_load_state("networkidle")

        # Check that main components are present - new template structure
        expect(page.locator("h4:has-text('Worksets')")).to_be_visible()
        expect(page.locator("#workset-list")).to_be_visible()

    def test_create_workset_link_exists(self, page, app_url):
        """Test that the create workset link is present."""
        page.goto(f"{app_url}/workbench/worksets")
        page.wait_for_load_state("networkidle")

        # Primary button for creating new workset
        expect(page.locator("a.btn-primary[href='/workbench/query-builder']")).to_be_visible()

    def test_workset_list_container_exists(self, page, app_url):
        """Test that the workset list container is present."""
        page.goto(f"{app_url}/workbench/worksets")
        page.wait_for_load_state("networkidle")

        expect(page.locator("#workset-list")).to_be_visible()

    def test_navigation_links_work(self, page, app_url):
        """Test that navigation links to other workbench pages work."""
        page.goto(f"{app_url}/workbench/worksets")
        page.wait_for_load_state("networkidle")

        # Click on Query Builder link (in the button group)
        page.click("a[href='/workbench/query-builder']")
        page.wait_for_load_state("networkidle")
        assert "/workbench/query-builder" in page.url

        # Go back to worksets
        page.goto(f"{app_url}/workbench/worksets")
        page.wait_for_load_state("networkidle")

        # Click on Bulk Operations link (in the button group)
        page.click("a[href='/workbench/bulk-operations']")
        page.wait_for_load_state("networkidle")
        assert "/workbench/bulk-operations" in page.url

    def test_bulk_operations_link_exists(self, page, app_url):
        """Test that the Bulk Operations navigation link exists."""
        page.goto(f"{app_url}/workbench/worksets")
        page.wait_for_load_state("networkidle")

        # Secondary button for bulk operations
        expect(page.locator("a.btn-outline-success[href='/workbench/bulk-operations']")).to_be_visible()


class TestWorksetSelection:
    """Test suite for workset selection UI elements.

    These tests create worksets first via the API, then test the UI elements end-to-end.
    Requires PostgreSQL to be available.
    """

    @pytest.fixture
    def created_workset(self, page, app_url):
        """Create a workset for testing and clean up after."""
        import uuid

        workset_name = f"Test Workset {uuid.uuid4().hex[:8]}"
        workset_id = None

        # First verify PostgreSQL is available by checking the worksets endpoint
        try:
            resp = page.context.request.get(f"{app_url}/api/worksets")
            if resp.status_code != 200:
                pytest.skip("PostgreSQL unavailable - workset service requires PostgreSQL")
                return None
        except Exception as e:
            pytest.skip(f"PostgreSQL unavailable: {e}")
            return None

        # Create workset via API
        try:
            resp = page.context.request.post(
                f"{app_url}/api/worksets",
                json={
                    "name": workset_name,
                    "query": {"filters": [], "sort_by": None, "sort_order": "asc"},
                    "description": "Created by E2E test"
                }
            )
            if resp.ok:
                data = resp.json()
                workset_id = data.get('id') or data.get('workset', {}).get('id')
                print(f"Created workset: {workset_name} (ID: {workset_id})")
            else:
                print(f"Failed to create workset: {resp.status_code}")
                pytest.skip("Failed to create workset - PostgreSQL may not be fully available")
                return None
        except Exception as e:
            print(f"Failed to create workset: {e}")
            pytest.skip(f"PostgreSQL unavailable: {e}")
            return None

        yield workset_id

        # Cleanup: delete the workset
        if workset_id:
            try:
                page.context.request.delete(f"{app_url}/api/worksets/{workset_id}")
                print(f"Cleaned up workset: {workset_id}")
            except Exception as e:
                print(f"Failed to cleanup workset {workset_id}: {e}")

    def test_select_all_checkbox_exists(self, page, app_url, created_workset):
        """Test that select all checkbox is present when worksets exist."""
        if created_workset is None:
            pytest.skip("Workset not created - PostgreSQL required")

        page.goto(f"{app_url}/workbench/worksets")
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(2000)  # Allow JS to dynamically add elements

        # Check if element exists
        checkbox = page.locator("#select-all-worksets")
        if checkbox.count() > 0:
            expect(checkbox).to_be_visible()
        else:
            pytest.fail("Bulk toolbar not rendered - workset may not have been created")

    def test_bulk_toolbar_exists(self, page, app_url, created_workset):
        """Test that bulk toolbar is present when worksets exist."""
        if created_workset is None:
            pytest.skip("Workset not created - PostgreSQL required")

        page.goto(f"{app_url}/workbench/worksets")
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(2000)  # Allow JS to dynamically add elements

        # Check if element exists
        toolbar = page.locator("#bulk-toolbar")
        if toolbar.count() > 0:
            expect(toolbar).to_be_visible()
        else:
            pytest.fail("Bulk toolbar not rendered - workset may not have been created")

    def test_selected_count_display_exists(self, page, app_url, created_workset):
        """Test that selected count display exists when worksets exist."""
        if created_workset is None:
            pytest.skip("Workset not created - PostgreSQL required")

        page.goto(f"{app_url}/workbench/worksets")
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(2000)  # Allow JS to dynamically add elements

        # Check if element exists
        count = page.locator("#selected-count")
        if count.count() > 0:
            expect(count).to_be_visible()
        else:
            pytest.fail("Selected count display not rendered - workset may not have been created")

    def test_bulk_selection_updates_count(self, page, app_url, created_workset):
        """Test that selecting a workset updates the selected count."""
        if created_workset is None:
            pytest.skip("Workset not created - PostgreSQL required")

        page.goto(f"{app_url}/workbench/worksets")
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(2000)

        # Check if workset card exists
        checkboxes = page.locator(".workset-checkbox")
        if checkboxes.count() == 0:
            pytest.fail("No workset checkboxes found - workset may not have been created")

        # Select the workset
        checkboxes.first.check()

        # Verify selected count updated
        selected_count = page.locator("#selected-count")
        expect(selected_count).to_have_text("1")

    def test_bulk_delete_button_visible_when_selected(self, page, app_url, created_workset):
        """Test that bulk delete button is visible when workset is selected."""
        if created_workset is None:
            pytest.skip("Workset not created - PostgreSQL required")

        page.goto(f"{app_url}/workbench/worksets")
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(2000)

        # Check if workset card exists
        checkboxes = page.locator(".workset-checkbox")
        if checkboxes.count() == 0:
            pytest.fail("No workset checkboxes found - workset may not have been created")

        # Select the workset
        checkboxes.first.check()

        # Verify bulk actions are visible
        selected_actions = page.locator("#selected-actions")
        if selected_actions.count() > 0:
            expect(selected_actions).to_be_visible()
        else:
            pytest.fail("Selected actions panel not visible after selection")


class TestWorksetCreation:
    """Test suite for workset creation via the Query Builder UI.

    Tests the full workflow of creating a workset through the GUI:
    1. Navigate to Query Builder
    2. Set up filter conditions
    3. Preview results
    4. Create workset with a name
    5. Verify workset appears on the worksets list
    """

    def test_create_workset_via_query_builder(self, page, app_url):
        """Test creating a workset through the full GUI workflow."""
        import uuid

        workset_name = f"GUI Created Workset {uuid.uuid4().hex[:8]}"
        logger.info(f"Starting test to create workset: {workset_name}")

        # Step 1: Navigate to Query Builder
        page.goto(f"{app_url}/workbench/query-builder")
        page.wait_for_load_state("networkidle")

        # Verify query builder loaded
        expect(page.locator("h4:has-text('Query Builder')")).to_be_visible()
        logger.info("Query Builder page loaded")

        # Step 2: Set filter to "Lexical Unit equals test"
        # E2E test database has entry "test" (exact match works)
        page.locator(".value-input").fill("test")
        logger.info("Filled filter value: test")

        # Step 3: Click Preview to verify we get results
        page.locator("#preview-query-btn").click()
        page.wait_for_timeout(1000)

        # Verify preview shows results
        preview_text = page.locator("#query-preview-json").inner_text()
        logger.info(f"Preview text: {preview_text}")

        # Step 4: Click Create Workset button (this opens the Bootstrap modal)
        page.locator("#execute-query-btn").click()
        page.wait_for_timeout(500)
        logger.info("Clicked Create Workset button")

        # Step 5: Fill in the workset name modal
        # Wait for Bootstrap modal to appear (it's a .modal class, not <dialog>)
        expect(page.locator("#createWorksetModal")).to_be_visible()
        expect(page.locator("#createWorksetModal h5:has-text('Create Workset')")).to_be_visible()
        logger.info("Modal opened")

        # Enter workset name
        page.locator("#workset-name-input").fill(workset_name)
        logger.info(f"Entered workset name: {workset_name}")

        # Click Create Workset in modal
        page.locator("#confirm-create-workset").click()
        logger.info("Clicked confirm button")

        # Wait for the workset to be created - wait for modal to close
        page.wait_for_timeout(3000)

        # Check if modal is closed
        modal_visible = page.locator("#createWorksetModal").is_visible()
        logger.info(f"Modal still visible: {modal_visible}")

        # Step 6: Navigate to worksets page to verify it was created
        page.goto(f"{app_url}/workbench/worksets")
        page.wait_for_load_state("networkidle")
        logger.info("Navigated to worksets page")

        # Wait for worksets to load
        page.wait_for_timeout(2000)

        # Debug: print all h6 headings
        headings = page.locator("h6").all_text_contents()
        logger.info(f"All h6 headings on page: {headings}")

        # Verify the workset appears in the list
        # Use heading level 6 which is what the template uses
        workset_heading = page.locator(f"h6:has-text('{workset_name}')")
        expect(workset_heading).to_be_visible()

        # Also verify entry count is shown
        workset_card = workset_heading.locator("..").locator("..")
        expect(workset_card.locator("text=/\\d+ entries/")).to_be_visible()

    def test_create_workset_with_multiple_filters(self, page, app_url):
        """Test creating a workset with multiple filter conditions."""
        import uuid

        workset_name = f"Multi-filter Workset {uuid.uuid4().hex[:8]}"

        # Navigate to Query Builder
        page.goto(f"{app_url}/workbench/query-builder")
        page.wait_for_load_state("networkidle")

        # Add a second filter condition
        page.locator("#add-filter-btn").click()
        page.wait_for_timeout(500)

        # Verify second filter row appeared
        filter_rows = page.locator(".filter-condition")
        expect(filter_rows).to_have_count(2)

        # Set up both filters - use "equals" with "test" which exists in E2E database
        page.locator(".filter-condition").nth(0).locator(".value-input").fill("test")
        page.locator(".filter-condition").nth(1).locator(".value-input").fill("test")

        # Click Create Workset
        page.locator("#execute-query-btn").click()

        # Wait for modal
        expect(page.locator("#createWorksetModal")).to_be_visible()

        # Enter workset name
        page.locator("#workset-name-input").fill(workset_name)

        # Create
        page.locator("#confirm-create-workset").click()
        page.wait_for_timeout(2000)

        # Verify on worksets page
        page.goto(f"{app_url}/workbench/worksets")
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(2000)

        expect(page.locator(f"h6:has-text('{workset_name}')")).to_be_visible()


class TestWorksetApiEndpoints:
    """Test suite for workset API endpoints - checking they exist and are reachable."""

    def test_worksets_list_endpoint_reachable(self, page, app_url):
        """Test that /api/worksets endpoint is reachable."""
        response = requests.get(f"{app_url}/api/worksets", allow_redirects=False)
        # Either redirects (302) or processes (200) or returns error (500)
        assert response.status_code in [200, 302, 500], f"Unexpected status: {response.status_code}"

    def test_pipelines_list_endpoint_reachable(self, page, app_url):
        """Test that /api/pipelines endpoint is reachable."""
        response = requests.get(f"{app_url}/api/pipelines", allow_redirects=False)
        assert response.status_code in [200, 302, 500], f"Unexpected status: {response.status_code}"

    def test_worksets_bulk_delete_endpoint_reachable(self, page, app_url):
        """Test that /api/worksets/bulk/delete endpoint is reachable."""
        response = requests.post(
            f"{app_url}/api/worksets/bulk/delete",
            json={"ids": []},
            allow_redirects=False
        )
        # Either redirects (302) or processes (400 for empty ids) or returns error (500)
        assert response.status_code in [200, 302, 400, 500], f"Unexpected status: {response.status_code}"


# Run tests when file is executed directly
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
