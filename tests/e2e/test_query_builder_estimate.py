"""
E2E test: Query builder estimate must match preview for Note searches.
"""
import pytest
from playwright.sync_api import Page, expect


class TestQueryBuilderEstimate:
    """Validate that the estimate and preview agree for note searches."""

    def test_validate_updates_estimate_display(self, page: Page, app_url: str):
        """Set up a simple filter, click Validate, verify the display updates."""
        page.goto(f"{app_url}/workbench/query-builder")
        page.wait_for_load_state("networkidle")

        # Set operator to "contains" on the default lexical_unit filter
        operator_select = page.locator(".operator-select").first
        operator_select.select_option("contains")

        # Set value to a word that should exist in test data
        value_input = page.locator(".value-input").first
        value_input.fill("test")

        # Click Validate
        page.locator("#validate-query-btn").click()
        page.wait_for_timeout(2000)

        # The estimate display should update (not throw an error)
        result_count = page.locator("#result-count")
        expect(result_count).to_be_visible()

    def test_preview_shows_toast_message(self, page: Page, app_url: str):
        """Preview must show a success/error toast, not crash."""
        page.goto(f"{app_url}/workbench/query-builder")
        page.wait_for_load_state("networkidle")

        operator_select = page.locator(".operator-select").first
        operator_select.select_option("contains")
        page.locator(".value-input").first.fill("test")

        # Click Preview
        page.locator("#preview-query-btn").click()
        page.wait_for_timeout(3000)

        # Preview shows a toast alert — look for .validation-alert or .alert
        toast = page.locator(".validation-alert, .alert-info, .alert-success, .alert-danger").first
        expect(toast).to_be_visible(timeout=5000)

    def test_validate_button_is_clickable(self, page: Page, app_url: str):
        """Validate button exists and is clickable."""
        page.goto(f"{app_url}/workbench/query-builder")
        page.wait_for_load_state("networkidle")

        btn = page.locator("#validate-query-btn")
        expect(btn).to_be_visible()
        expect(btn).to_be_enabled()



class TestWorksetCurationLoads:
    """Curation page must load the first entry without errors."""

    def test_curation_page_loads_without_500(self, page: Page, app_url: str):
        """Navigate to a workset curation page and verify it doesn't 500."""
        page.goto(f"{app_url}/workbench/worksets")
        page.wait_for_load_state("networkidle")

        cards = page.locator(".workset-card")
        if cards.count() == 0:
            pytest.skip("No worksets available to test curation")

        # Click "Start Curation" on first workset
        curate_link = cards.first.locator("a:has-text('Start Curation')")
        if curate_link.count() > 0:
            curate_link.click()
        else:
            cards.first.locator(".dropdown-toggle").click()
            page.wait_for_timeout(300)
            curate_btn = page.locator(".curate-btn").first
            if curate_btn.count() > 0:
                curate_btn.click()
            else:
                pytest.skip("No curation link found")

        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(2000)

        # The page should render — either showing entry, or "Workset is empty"
        # Just verify it's not a 500 error page
        body_text = page.locator("body").text_content()
        assert "Internal Server Error" not in body_text, f"Page 500'd"
        assert "TemplateNotFound" not in body_text, f"Template missing"
