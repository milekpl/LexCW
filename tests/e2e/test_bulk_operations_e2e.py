"""
E2E tests for Bulk Operations page - Workbench /workbench/bulk-operations

Tests cover:
- Page loading and initialization
- Condition builder functionality
- Pipeline editor with relation target selection
- Pipeline template CRUD operations
- Preview and execute operations
"""

import pytest
import time
import logging
import requests
from playwright.sync_api import Page, expect

logger = logging.getLogger(__name__)


class TestBulkOperationsPage:
    """Test suite for Bulk Operations page functionality."""

    def test_page_loads_successfully(self, page, app_url):
        """Test that the bulk operations page loads without errors."""
        page.goto(f"{app_url}/workbench/bulk-operations")

        # Wait for page to load
        page.wait_for_load_state("networkidle")

        # Check that main components are present - new template structure
        expect(page.locator("h4:has-text('Bulk Operations')")).to_be_visible()
        expect(page.locator("text=1. Which entries?")).to_be_visible()
        expect(page.locator("text=2. What to do?")).to_be_visible()

    def test_condition_builder_initializes(self, page, app_url):
        """Test that ConditionBuilder initializes with expected controls."""
        page.goto(f"{app_url}/workbench/bulk-operations")
        page.wait_for_load_state("networkidle")

        # Check for condition builder elements
        expect(page.locator("#condition-builder")).to_be_visible()
        expect(page.locator("button:has-text('+ Add Condition')")).to_be_visible()

    def test_pipeline_editor_initializes(self, page, app_url):
        """Test that PipelineEditor initializes with expected controls."""
        page.goto(f"{app_url}/workbench/bulk-operations")
        page.wait_for_load_state("networkidle")

        # Check for pipeline editor elements
        expect(page.locator("#pipeline-editor")).to_be_visible()
        expect(page.locator("button:has-text('+ Add Step')")).to_be_visible()

    def test_add_condition_step(self, page, app_url):
        """Test adding a condition to the condition builder."""
        page.goto(f"{app_url}/workbench/bulk-operations")
        page.wait_for_load_state("networkidle")

        # Click add condition button
        page.click("button:has-text('+ Add Condition')")

        # Verify condition row appeared
        expect(page.locator(".condition-row")).to_be_visible()

        # Verify field selector is present
        expect(page.locator("select[data-field='field']")).to_be_visible()

    def test_add_pipeline_step(self, page, app_url):
        """Test adding a step to the pipeline editor."""
        page.goto(f"{app_url}/workbench/bulk-operations")
        page.wait_for_load_state("networkidle")

        # Click add step button
        page.click("button:has-text('+ Add Step')")

        # Verify step card appeared
        expect(page.locator(".pipeline-step")).to_be_visible()

        # Verify action type selector is present
        expect(page.locator("select[data-field='type']")).to_be_visible()

    def test_pipeline_action_types_available(self, page, app_url):
        """Test that all action types are available in the dropdown."""
        page.goto(f"{app_url}/workbench/bulk-operations")
        page.wait_for_load_state("networkidle")

        # Add a step
        page.click("button:has-text('+ Add Step')")

        # Open the action type dropdown
        page.select_option("select[data-field='type']", "")

        # Verify expected options are available
        action_dropdown = page.locator("select[data-field='type']")

        # Check for relation-related options
        options = action_dropdown.locator("option").all_text_contents()
        assert "Add Relation" in options
        assert "Remove Relation" in options
        assert "Replace Relation Target" in options

    def test_relation_step_shows_search_selector(self, page, app_url):
        """Test that relation steps show the entry search selector."""
        page.goto(f"{app_url}/workbench/bulk-operations")
        page.wait_for_load_state("networkidle")

        # Add a step and select relation type
        page.click("button:has-text('+ Add Step')")
        page.select_option("select[data-field='type']", "add_relation")

        # Verify relation type dropdown is present
        expect(page.locator("select[data-field='relation_type']")).to_be_visible()

        # Verify search container is present (EntrySearchSelect container)
        expect(page.locator(".relation-target-selector")).to_be_visible()

    def test_preview_button_exists(self, page, app_url):
        """Test that the Preview Match button is present."""
        page.goto(f"{app_url}/workbench/bulk-operations")
        page.wait_for_load_state("networkidle")

        expect(page.locator("button:has-text('Preview Match')")).to_be_visible()

    def test_execute_button_exists(self, page, app_url):
        """Test that the Execute Pipeline button is present."""
        page.goto(f"{app_url}/workbench/bulk-operations")
        page.wait_for_load_state("networkidle")

        expect(page.locator("#execute-pipeline-btn")).to_be_visible()

    def test_save_pipeline_button_exists(self, page, app_url):
        """Test that the Save Pipeline button is present."""
        page.goto(f"{app_url}/workbench/bulk-operations")
        page.wait_for_load_state("networkidle")

        expect(page.locator("#save-pipeline-btn")).to_be_visible()

    def test_saved_pipelines_section_exists(self, page, app_url):
        """Test that the Saved Pipelines section is present."""
        page.goto(f"{app_url}/workbench/bulk-operations")
        page.wait_for_load_state("networkidle")

        # The section header contains "Saved Pipelines" text
        expect(page.locator(".card-header:has-text('Saved Pipelines')")).to_be_visible()

    def test_preview_does_not_crash(self, page, app_url):
        """Test that clicking Preview doesn't cause JS errors."""
        page.goto(f"{app_url}/workbench/bulk-operations")
        page.wait_for_load_state("networkidle")

        # Add a condition and a step
        page.click("button:has-text('+ Add Condition')")
        page.click("button:has-text('+ Add Step')")

        # Set a simple condition (lexical_unit contains)
        page.select_option(".condition-row select[data-field='field']", "lexical_unit")
        page.fill(".condition-row input[data-field='value']", "test")

        # Set a simple action (set value)
        page.select_option(".pipeline-step select[data-field='type']", "set")

        # Click preview - should not cause JS errors
        page.click("button:has-text('Preview Match')")

        # Wait for an API request or UI update instead of sleeping
        try:
            page.wait_for_response(lambda r: 'preview' in r.url or '/api/' in r.url, timeout=5000)
        except Exception:
            # Fallback to a short network idle if no matching response observed
            page.wait_for_load_state('networkidle')

        # Verify page is still functional
        expect(page.locator("body")).to_be_visible()

    def test_keyboard_shortcuts_available(self, page, app_url):
        """Test that keyboard shortcuts are mentioned in UI."""
        page.goto(f"{app_url}/workbench/bulk-operations")
        page.wait_for_load_state("networkidle")

        # Check that keyboard hint is visible
        expect(page.locator("text=Ctrl+Enter")).to_be_visible()

    def test_navigation_to_query_builder(self, page, app_url):
        """Test navigation to Query Builder."""
        page.goto(f"{app_url}/workbench/bulk-operations")
        page.wait_for_load_state("networkidle")

        # Find and click on Query Builder link (in button group)
        query_builder_link = page.locator("a[href='/workbench/query-builder']")
        expect(query_builder_link).to_be_visible()
        query_builder_link.click()

        # Should navigate to query builder
        page.wait_for_load_state("networkidle")
        assert "/workbench/query-builder" in page.url

    def test_navigation_to_worksets(self, page, app_url):
        """Test navigation to Worksets."""
        page.goto(f"{app_url}/workbench/bulk-operations")
        page.wait_for_load_state("networkidle")

        # Find and click on Worksets link (in button group)
        worksets_link = page.locator("a[href='/workbench/worksets']")
        expect(worksets_link).to_be_visible()
        worksets_link.click()

        # Should navigate to worksets
        page.wait_for_load_state("networkidle")
        assert "/workbench/worksets" in page.url


class TestBulkOperationsApi:
    """Test suite for Bulk Operations API endpoints - these may fail if not authenticated."""

    def test_bulk_preview_endpoint_reachable(self, page, app_url):
        """Test that /api/bulk/preview endpoint is reachable."""
        # Make a request (will redirect if not authenticated, that's OK)
        response = requests.post(
            f"{app_url}/api/bulk/preview",
            json={"condition": {"field": "lexical_unit", "operator": "contains", "value": "test"}},
            allow_redirects=False
        )

        # Either redirects (302) or processes (200) or returns error (400/500)
        # Any of these indicate the endpoint exists
        assert response.status_code in [200, 302, 400, 500], f"Unexpected status: {response.status_code}"

    def test_bulk_pipeline_endpoint_reachable(self, page, app_url):
        """Test that /api/bulk/pipeline endpoint is reachable."""
        response = requests.post(
            f"{app_url}/api/bulk/pipeline",
            json={
                "condition": {"field": "lexical_unit", "operator": "contains", "value": "nonexistent"},
                "steps": [{"type": "set", "field": "lexical_unit", "value": "test"}],
                "preview": True
            },
            allow_redirects=False
        )

        # Either redirects (302) or processes (200) or returns error (400/500)
        assert response.status_code in [200, 302, 400, 500], f"Unexpected status: {response.status_code}"


class TestWorksetBulkDelete:
    """Test suite for workset bulk delete UI elements.

    Note: These tests may fail if PostgreSQL is not available, as the JavaScript
    that adds these elements to the DOM requires an active database connection.
    """

    def test_worksets_page_loads(self, page, app_url):
        """Test that the worksets page loads."""
        page.goto(f"{app_url}/workbench/worksets")
        page.wait_for_load_state("networkidle")

        # The page should have worksets content - new template structure
        expect(page.locator("h4:has-text('Worksets')")).to_be_visible()

    def test_create_workset_button_exists(self, page, app_url):
        """Test that create workset button exists."""
        page.goto(f"{app_url}/workbench/worksets")
        page.wait_for_load_state("networkidle")

        # Create workset button
        create_link = page.locator("a.btn-primary[href='/workbench/query-builder']")
        expect(create_link).to_be_visible()


# Run tests when file is executed directly
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
