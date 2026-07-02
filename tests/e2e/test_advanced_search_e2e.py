"""
E2E tests for Advanced Search features.

Tests cover:
- Faceted search navigation
- Search within results
- Save/load search queries
- Search result export (CSV, JSON)
"""

import pytest
import time
import logging
from playwright.sync_api import Page, expect

logger = logging.getLogger(__name__)


def _perform_search_via_api(page, app_url, query, pos=""):
    """Helper: perform search by setting URL params and letting JS pick them up."""
    params = f"q={query}"
    if pos:
        params += f"&pos={pos}"
    page.goto(f"{app_url}/search?{params}")
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(2000)


class TestFacetedSearch:
    """Test suite for faceted search navigation."""

    def test_facet_sidebar_appears_after_search(self, page: Page, app_url: str):
        """After performing a search, the facet sidebar should be visible."""
        _perform_search_via_api(page, app_url, "a")
        facet_section = page.locator("#facet-sidebar")
        expect(facet_section).to_be_visible()

    def test_facet_shows_grammatical_info_counts(self, page: Page, app_url: str):
        """Facet sidebar should show grammatical-info with correct counts."""
        _perform_search_via_api(page, app_url, "a")
        noun_facet = page.locator(".facet-value[data-facet-value='Noun']")
        expect(noun_facet).to_be_visible()
        expect(noun_facet).to_contain_text("Noun")
        count = noun_facet.locator(".facet-count")
        expect(count).to_contain_text("2")

    def test_clicking_facet_filters_results(self, page: Page, app_url: str):
        """Clicking a facet value should filter results to that category."""
        _perform_search_via_api(page, app_url, "a")
        noun_facet = page.locator(".facet-value[data-facet-value='Noun']")
        noun_facet.click()
        page.wait_for_timeout(2000)

        result_count = page.locator("#results-count")
        expect(result_count).to_contain_text("2 results")

    def test_active_facet_shows_remove_button(self, page: Page, app_url: str):
        """When a facet is active, it should show a remove/clear indicator."""
        _perform_search_via_api(page, app_url, "a")
        noun_facet = page.locator(".facet-value[data-facet-value='Noun']")
        noun_facet.click()
        page.wait_for_timeout(2000)

        active_filter = page.locator("#active-filters .active-filter")
        expect(active_filter).to_be_visible()

    def test_removing_facet_returns_to_unfiltered(self, page: Page, app_url: str):
        """Removing an active facet should return to full results."""
        _perform_search_via_api(page, app_url, "a")
        noun_facet = page.locator(".facet-value[data-facet-value='Noun']")
        noun_facet.click()
        page.wait_for_timeout(2000)

        remove_btn = page.locator("#active-filters .active-filter .remove-facet")
        remove_btn.click()
        page.wait_for_timeout(2000)

        result_count = page.locator("#results-count")
        expect(result_count).to_contain_text("3 results")


class TestSearchWithinResults:
    """Test suite for 'search within results' feature."""

    def test_search_within_input_appears_after_search(self, page: Page, app_url: str):
        """After a search, the 'filter within results' input should appear."""
        _perform_search_via_api(page, app_url, "a")
        within_input = page.locator("#search-within-results")
        expect(within_input).to_be_visible()

    def test_search_within_narrows_results(self, page: Page, app_url: str):
        """Typing in 'filter within results' should narrow displayed results."""
        _perform_search_via_api(page, app_url, "a")
        within_input = page.locator("#search-within-results")
        within_input.fill("dog")
        within_input.press("Enter")
        page.wait_for_timeout(1000)

        visible_results = page.locator(".search-result")
        expect(visible_results).to_have_count(1)

    def test_search_within_clear_shows_all(self, page: Page, app_url: str):
        """Clearing the 'filter within results' should show all results again."""
        _perform_search_via_api(page, app_url, "a")
        within_input = page.locator("#search-within-results")
        within_input.fill("dog")
        within_input.press("Enter")
        page.wait_for_timeout(500)
        within_input.clear()
        within_input.press("Enter")
        page.wait_for_timeout(500)

        visible_results = page.locator(".search-result")
        expect(visible_results).to_have_count(3)


class TestSearchResultExport:
    """Test suite for search result export."""

    def test_export_buttons_visible_after_search(self, page: Page, app_url: str):
        """Export buttons should appear after performing a search."""
        _perform_search_via_api(page, app_url, "cat")
        export_csv = page.locator("#export-csv-btn")
        export_json = page.locator("#export-json-btn")
        expect(export_csv).to_be_visible()
        expect(export_json).to_be_visible()

    def test_export_csv_triggers_download(self, page: Page, app_url: str):
        """Clicking CSV export should trigger a download."""
        _perform_search_via_api(page, app_url, "cat")
        with page.expect_download() as download_info:
            page.click("#export-csv-btn")
        download = download_info.value
        assert download.suggested_filename.endswith('.csv')

    def test_export_json_triggers_download(self, page: Page, app_url: str):
        """Clicking JSON export should trigger a download."""
        _perform_search_via_api(page, app_url, "cat")
        with page.expect_download() as download_info:
            page.click("#export-json-btn")
        download = download_info.value
        assert download.suggested_filename.endswith('.json')


class TestSaveLoadSearch:
    """Test suite for saving and loading search queries."""

    def test_save_search_button_appears_after_search(self, page: Page, app_url: str):
        """Save search button should appear after performing a search."""
        _perform_search_via_api(page, app_url, "cat")
        save_btn = page.locator("#save-search-btn")
        expect(save_btn).to_be_visible()

    def test_save_search_opens_modal(self, page: Page, app_url: str):
        """Clicking save search should open a modal to name the search."""
        _perform_search_via_api(page, app_url, "cat")
        page.click("#save-search-btn")
        save_modal = page.locator("#save-search-modal")
        expect(save_modal).to_be_visible()

    def test_save_and_load_search(self, page: Page, app_url: str):
        """Saving a search and then loading it should work."""
        _perform_search_via_api(page, app_url, "cat")
        page.click("#save-search-btn")
        name_input = page.locator("#save-search-name")
        name_input.fill("Cat Search")
        page.click("#save-search-confirm")
        page.wait_for_timeout(500)

        _perform_search_via_api(page, app_url, "dog")

        saved_search = page.locator(".saved-search-item:has-text('Cat Search')")
        expect(saved_search).to_be_visible()
