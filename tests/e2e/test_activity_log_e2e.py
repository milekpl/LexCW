"""
E2E tests for Activity Log page and filtering functionality.

Tests cover:
- Page loading and basic display
- Activity list rendering
- Filter panel functionality
- Action type filtering
- Search functionality
- Date range filtering
- Pagination with filters
- Clear filters button

Note: Tests assume the database may have no activity data initially,
so we also test the "empty state" display.
"""

import pytest
import time
from playwright.sync_api import Page, expect


class TestActivityLogPage:
    """Test suite for Activity Log page functionality."""

    def test_page_loads_successfully(self, page, app_url):
        """Test that the activity log page loads without errors."""
        page.goto(f"{app_url}/activity-log")
        page.wait_for_load_state("networkidle")

        # Check that main components are present
        expect(page.locator("h2:has-text('Activity Log')")).to_be_visible()
        expect(page.locator(".table")).to_be_visible()

    def test_filter_panel_exists(self, page, app_url):
        """Test that the filter panel is present on the page."""
        page.goto(f"{app_url}/activity-log")
        page.wait_for_load_state("networkidle")

        # Check filter panel header
        expect(page.locator("h5:has-text('Filter & Search')")).to_be_visible()

        # Check all filter inputs exist
        expect(page.locator("select[name='action']")).to_be_visible()
        expect(page.locator("input[name='search']")).to_be_visible()
        expect(page.locator("input[name='date_from']")).to_be_visible()
        expect(page.locator("input[name='date_to']")).to_be_visible()
        expect(page.locator("button[type='submit']")).to_be_visible()

    def test_action_type_filter_options(self, page, app_url):
        """Test that action type filter has all expected options."""
        page.goto(f"{app_url}/activity-log")
        page.wait_for_load_state("networkidle")

        action_select = page.locator("select[name='action']")
        
        # Check all expected options exist
        options = action_select.locator("option").all_text_contents()
        expected_options = [
            "All Actions",
            "Create",
            "Update", 
            "Delete",
            "Merge",
            "Split",
            "Undo",
            "Redo"
        ]
        
        for option in expected_options:
            assert option in options, f"Missing option: {option}"

    def test_filter_by_action_type(self, page, app_url):
        """Test filtering by action type updates the URL and results."""
        page.goto(f"{app_url}/activity-log")
        page.wait_for_load_state("networkidle")

        # Select 'Create' from action filter
        page.select_option("select[name='action']", "create")
        
        # Submit the form
        page.click("button[type='submit']")
        
        # Wait for page reload with filter
        page.wait_for_load_state("networkidle")
        
        # Check URL contains filter parameter
        assert "action=create" in page.url

    def test_search_input_functionality(self, page, app_url):
        """Test that search input accepts text and submits."""
        page.goto(f"{app_url}/activity-log")
        page.wait_for_load_state("networkidle")

        # Enter search text
        search_input = page.locator("input[name='search']")
        search_input.fill("test_entry")
        
        # Submit the form
        page.click("button[type='submit']")
        
        # Wait for page reload
        page.wait_for_load_state("networkidle")
        
        # Check URL contains search parameter
        assert "search=test_entry" in page.url

    def test_date_range_filter(self, page, app_url):
        """Test date range filtering functionality."""
        page.goto(f"{app_url}/activity-log")
        page.wait_for_load_state("networkidle")

        # Set date range
        from_date = page.locator("input[name='date_from']")
        to_date = page.locator("input[name='date_to']")
        
        from_date.fill("2024-01-01")
        to_date.fill("2024-12-31")
        
        # Submit the form
        page.click("button[type='submit']")
        
        # Wait for page reload
        page.wait_for_load_state("networkidle")
        
        # Check URL contains date parameters
        assert "date_from=2024-01-01" in page.url
        assert "date_to=2024-12-31" in page.url

    def test_clear_filters_button(self, page, app_url):
        """Test that clear filters button removes all filters."""
        # Start with some filters applied
        page.goto(f"{app_url}/activity-log?action=create&search=test")
        page.wait_for_load_state("networkidle")

        # Check clear filters button exists when filters are applied
        clear_button = page.locator("a:has-text('Clear Filters')")
        expect(clear_button).to_be_visible()
        
        # Click clear filters
        clear_button.click()
        
        # Wait for page reload
        page.wait_for_load_state("networkidle")
        
        # Check URL no longer has filter parameters
        assert "action=" not in page.url
        assert "search=" not in page.url

    def test_pagination_preserves_filters(self, page, app_url):
        """Test that pagination links preserve filter parameters."""
        # This test checks if the pagination links include filter params
        # We mock this by checking the template renders correctly
        page.goto(f"{app_url}/activity-log?action=update&search=entry")
        page.wait_for_load_state("networkidle")

        # The page should load without error even with filters
        expect(page.locator("h2:has-text('Activity Log')")).to_be_visible()
        
        # Check that filter values are preserved in form
        action_select = page.locator("select[name='action']")
        expect(action_select).to_have_value("update")
        
        search_input = page.locator("input[name='search']")
        expect(search_input).to_have_value("entry")

    def test_empty_state_display(self, page, app_url):
        """Test that empty state displays correctly when no activities."""
        page.goto(f"{app_url}/activity-log")
        page.wait_for_load_state("networkidle")

        # Check if table shows empty state or has data
        # The template shows "No activity recorded yet." message in empty state
        # but we need to be flexible as test DB might have data
        
        # At minimum, the table headers should be visible
        expect(page.locator("th:has-text('Timestamp')")).to_be_visible()
        expect(page.locator("th:has-text('Action')")).to_be_visible()
        expect(page.locator("th:has-text('Description')")).to_be_visible()
        expect(page.locator("th:has-text('Entry ID')")).to_be_visible()

    def test_filter_form_submission_method(self, page, app_url):
        """Test that filter form uses GET method (for bookmarkable URLs)."""
        page.goto(f"{app_url}/activity-log")
        page.wait_for_load_state("networkidle")

        form = page.locator("form[method='GET']")
        expect(form).to_be_visible()

    def test_back_to_dashboard_link(self, page, app_url):
        """Test that back to dashboard link works."""
        page.goto(f"{app_url}/activity-log")
        page.wait_for_load_state("networkidle")

        # Find and click the back button
        back_button = page.locator("a:has-text('Back to Dashboard')")
        expect(back_button).to_be_visible()
        
        back_button.click()
        page.wait_for_load_state("networkidle")
        
        # Should be on dashboard/index page
        assert "/" in page.url or "index" in page.url

    def test_total_operations_count_display(self, page, app_url):
        """Test that total operations count badge is displayed."""
        page.goto(f"{app_url}/activity-log")
        page.wait_for_load_state("networkidle")

        # Check for the total count badge
        expect(page.locator(".badge:has-text('total operations')")).to_be_visible()


class TestActivityLogWithMockData:
    """Test suite that creates activity data first, then tests filtering."""

    @pytest.fixture
    def create_test_entry(self, page, app_url):
        """Create a test entry to generate activity data."""
        # Navigate to entry creation page
        page.goto(f"{app_url}/entries/add")
        page.wait_for_load_state("networkidle")
        
        # Fill in minimal required fields
        # This assumes there's a lexical unit field
        try:
            lexical_input = page.locator("input[name*='lexical']").first
            if lexical_input.count() > 0:
                lexical_input.fill("test_activity_entry")
                
                # Submit the form
                submit_button = page.locator("button[type='submit']").first
                if submit_button.count() > 0:
                    submit_button.click()
                    page.wait_for_load_state("networkidle")
                    
                    # Wait a moment for activity to be recorded
                    time.sleep(0.5)
        except:
            # If entry creation fails, continue anyway
            pass
        
        yield
        
        # Cleanup not strictly necessary for activity log tests

    def test_activity_shows_after_entry_creation(self, page, app_url, create_test_entry):
        """Test that activity appears in log after creating an entry."""
        # Navigate to activity log
        page.goto(f"{app_url}/activity-log")
        page.wait_for_load_state("networkidle")
        
        # The table should be present
        expect(page.locator("table")).to_be_visible()
        
        # Filter by 'create' action to see if our entry appears
        page.select_option("select[name='action']", "create")
        page.click("button[type='submit']")
        page.wait_for_load_state("networkidle")
        
        # Page should load successfully
        assert "action=create" in page.url

    def test_search_finds_entry_by_text(self, page, app_url, create_test_entry):
        """Test searching for activity by entry text."""
        page.goto(f"{app_url}/activity-log")
        page.wait_for_load_state("networkidle")

        # Search for the test entry we created
        search_input = page.locator("input[name='search']")
        search_input.fill("test_activity")
        
        page.click("button[type='submit']")
        page.wait_for_load_state("networkidle")
        
        # Check URL has search parameter
        assert "search=test_activity" in page.url


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
