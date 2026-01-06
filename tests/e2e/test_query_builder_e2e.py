"""
E2E tests for Query Builder page - Workbench /workbench/query-builder

Tests cover:
- Page loading and structure
- Filter conditions UI
- Navigation to worksets and bulk operations
- Query preview functionality
"""

import pytest
import time
import logging
import requests
from playwright.sync_api import Page, expect

logger = logging.getLogger(__name__)


class TestQueryBuilderPage:
    """Test suite for Query Builder page functionality."""

    def test_page_loads_successfully(self, page, app_url):
        """Test that the query builder page loads without errors."""
        page.goto(f"{app_url}/workbench/query-builder")
        page.wait_for_load_state("networkidle")

        # Check that main components are present
        expect(page.locator("h4:has-text('Query Builder')")).to_be_visible()
        expect(page.locator("#filter-conditions")).to_be_visible()

    def test_initial_filter_condition_present(self, page, app_url):
        """Test that an initial filter condition is present."""
        page.goto(f"{app_url}/workbench/query-builder")
        page.wait_for_load_state("networkidle")

        # First filter condition should be visible
        expect(page.locator(".filter-condition")).to_be_visible()
        expect(page.locator(".field-select")).to_be_visible()
        expect(page.locator(".operator-select")).to_be_visible()
        expect(page.locator(".value-input")).to_be_visible()

    def test_add_filter_button_exists(self, page, app_url):
        """Test that the Add Filter button exists."""
        page.goto(f"{app_url}/workbench/query-builder")
        page.wait_for_load_state("networkidle")

        expect(page.locator("#add-filter-btn")).to_be_visible()
        expect(page.locator("#add-filter-btn")).to_contain_text("Add Filter")

    def test_add_filter_button_works(self, page, app_url):
        """Test that clicking Add Filter adds a new condition."""
        page.goto(f"{app_url}/workbench/query-builder")
        page.wait_for_load_state("networkidle")

        # Count initial filters
        initial_count = page.locator(".filter-condition").count()

        # Click add filter button
        page.click("#add-filter-btn")

        # Verify new filter was added
        expect(page.locator(".filter-condition")).to_have_count(initial_count + 1)

    def test_sort_by_select_exists(self, page, app_url):
        """Test that the Sort by select dropdown exists."""
        page.goto(f"{app_url}/workbench/query-builder")
        page.wait_for_load_state("networkidle")

        expect(page.locator("#sort-by-select")).to_be_visible()

    def test_sort_order_select_exists(self, page, app_url):
        """Test that the Sort order select dropdown exists."""
        page.goto(f"{app_url}/workbench/query-builder")
        page.wait_for_load_state("networkidle")

        expect(page.locator("#sort-order-select")).to_be_visible()

    def test_validate_button_exists(self, page, app_url):
        """Test that the Validate button exists."""
        page.goto(f"{app_url}/workbench/query-builder")
        page.wait_for_load_state("networkidle")

        expect(page.locator("#validate-query-btn")).to_be_visible()

    def test_preview_button_exists(self, page, app_url):
        """Test that the Preview button exists."""
        page.goto(f"{app_url}/workbench/query-builder")
        page.wait_for_load_state("networkidle")

        expect(page.locator("#preview-query-btn")).to_be_visible()

    def test_create_workset_button_exists(self, page, app_url):
        """Test that the Create Workset button exists."""
        page.goto(f"{app_url}/workbench/query-builder")
        page.wait_for_load_state("networkidle")

        expect(page.locator("#execute-query-btn")).to_be_visible()

    def test_query_preview_exists(self, page, app_url):
        """Test that the Query Preview section exists."""
        page.goto(f"{app_url}/workbench/query-builder")
        page.wait_for_load_state("networkidle")

        expect(page.locator("#query-preview-json")).to_be_visible()

    def test_saved_queries_section_exists(self, page, app_url):
        """Test that the Saved Queries section exists."""
        page.goto(f"{app_url}/workbench/query-builder")
        page.wait_for_load_state("networkidle")

        expect(page.locator("#saved-queries-list")).to_be_visible()

    def test_navigation_to_worksets(self, page, app_url):
        """Test navigation to Worksets."""
        page.goto(f"{app_url}/workbench/query-builder")
        page.wait_for_load_state("networkidle")

        # Find and click on Worksets link (in button group)
        worksets_link = page.locator("a[href='/workbench/worksets']")
        expect(worksets_link).to_be_visible()
        worksets_link.click()

        # Should navigate to worksets
        page.wait_for_load_state("networkidle")
        assert "/workbench/worksets" in page.url

    def test_navigation_to_bulk_operations(self, page, app_url):
        """Test navigation to Bulk Operations."""
        page.goto(f"{app_url}/workbench/query-builder")
        page.wait_for_load_state("networkidle")

        # Find and click on Bulk Operations link (in button group)
        bulk_ops_link = page.locator("a[href='/workbench/bulk-operations']")
        expect(bulk_ops_link).to_be_visible()
        bulk_ops_link.click()

        # Should navigate to bulk operations
        page.wait_for_load_state("networkidle")
        assert "/workbench/bulk-operations" in page.url

    def test_worksets_link_from_button(self, page, app_url):
        """Test that Worksets link in button group works."""
        page.goto(f"{app_url}/workbench/query-builder")
        page.wait_for_load_state("networkidle")

        # Click on Worksets link
        page.click("a.btn-outline-primary[href='/workbench/worksets']")
        page.wait_for_load_state("networkidle")

        assert "/workbench/worksets" in page.url

    def test_bulk_operations_link_from_button(self, page, app_url):
        """Test that Bulk Operations link in button group works."""
        page.goto(f"{app_url}/workbench/query-builder")
        page.wait_for_load_state("networkidle")

        # Click on Bulk Operations link
        page.click("a.btn-outline-success[href='/workbench/bulk-operations']")
        page.wait_for_load_state("networkidle")

        assert "/workbench/bulk-operations" in page.url


class TestQueryBuilderApi:
    """Test suite for Query Builder API endpoints."""

    def test_query_validate_endpoint_reachable(self, page, app_url):
        """Test that /api/query-builder/validate endpoint is reachable."""
        response = requests.post(
            f"{app_url}/api/query-builder/validate",
            json={"filters": [], "sort_by": None, "sort_order": "asc"},
            allow_redirects=False
        )
        # Either redirects (302) or processes (200) or returns error
        assert response.status_code in [200, 302, 400, 500], f"Unexpected status: {response.status_code}"

    def test_query_preview_endpoint_reachable(self, page, app_url):
        """Test that /api/query-builder/preview endpoint is reachable."""
        response = requests.post(
            f"{app_url}/api/query-builder/preview",
            json={"filters": [], "sort_by": None, "sort_order": "asc", "limit": 10},
            allow_redirects=False
        )
        # Either redirects (302) or processes (200) or returns error
        assert response.status_code in [200, 302, 400, 500], f"Unexpected status: {response.status_code}"

    def test_query_execute_endpoint_reachable(self, page, app_url):
        """Test that /api/query-builder/execute endpoint is reachable."""
        response = requests.post(
            f"{app_url}/api/query-builder/execute",
            json={"workset_name": "Test Workset", "query": {"filters": [], "sort_by": None, "sort_order": "asc"}},
            allow_redirects=False
        )
        # Either redirects (302) or processes (200/201) or returns error
        assert response.status_code in [200, 201, 302, 400, 500], f"Unexpected status: {response.status_code}"


# Run tests when file is executed directly
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
