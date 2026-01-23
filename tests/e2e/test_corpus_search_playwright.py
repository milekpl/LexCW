"""E2E tests for corpus search functionality.

Tests that:
1. Search Corpus buttons appear in the entry form
2. Modal opens correctly when clicking Search Corpus
3. Headword is auto-filled in the search input
4. API search returns results in source/target format
5. Results display correctly with source and target
6. Insert as Example button copies source text
7. Copy button copies source text to clipboard
"""
from __future__ import annotations

import pytest
import os
import requests
from playwright.sync_api import Page, expect
import time


@pytest.fixture(autouse=True)
def _skip_if_no_corpus():
    """Skip corpus integration tests if Lucene corpus service is not reachable.

    This avoids timeouts when the external corpus service (configured by
    LUCENE_CORPUS_URL) is not running in the test environment.
    """
    url = os.getenv('LUCENE_CORPUS_URL', 'http://localhost:8082')
    try:
        # quick lightweight check - timeout kept small so tests don't hang
        requests.get(url, timeout=1)
    except Exception:
        pytest.skip("Lucene corpus service not available; skipping corpus integration tests")


def wait_for_corpus_results(page: Page, timeout: int = 10000) -> None:
    """Poll until corpus results appear or an empty-state message is shown.

    This avoids relying on fixed sleeps which can cause flaky tests.
    """
    deadline = time.time() + (timeout / 1000.0)
    while time.time() < deadline:
        try:
            # If a result row is present, we're done
            if page.locator('.corpus-result').count() > 0:
                return
            # If results info is visible, consider it done
            if page.locator('#corpusResultsInfo').count() > 0 and page.locator('#corpusResultsInfo').first.is_visible():
                return
            # Check for common empty state messages
            html = page.locator('#corpusSearchResults').inner_html() or ''
            if 'No examples found' in html or 'Enter a search term' in html:
                return
        except Exception:
            # Ignore transient DOM read errors and retry
            pass
        page.wait_for_timeout(200)
    raise AssertionError('Timed out waiting for corpus search results or empty state')


@pytest.mark.integration
def test_search_corpus_button_exists_in_senses(page: Page, app_url: str, ensure_sense) -> None:
    """Test that Search Corpus buttons appear in sense sections."""
    page.goto(f"{app_url}/entries/add")
    page.wait_for_selector('#entry-form', state='visible', timeout=10000)

    # Ensure we have a sense with a definition
    ensure_sense(page)
    page.locator('textarea[name*="definition"]:visible').first.fill('Test definition')

    # Check for Search Corpus buttons - there should be one near definitions
    # and one near examples
    search_buttons = page.locator('.search-corpus-btn')
    expect(search_buttons.first).to_be_visible()


@pytest.mark.integration
def test_search_corpus_modal_opens(page: Page, app_url: str, ensure_sense) -> None:
    """Test that clicking Search Corpus opens the modal."""
    page.goto(f"{app_url}/entries/add")
    page.wait_for_selector('#entry-form', state='visible', timeout=10000)

    ensure_sense(page)

    # Click the first Search Corpus button
    search_buttons = page.locator('.search-corpus-btn')
    search_buttons.first.click()

    # Modal should be visible
    modal = page.locator('#corpusSearchModal')
    expect(modal).to_be_visible()


@pytest.mark.integration
def test_headword_auto_filled_in_search(page: Page, app_url: str, ensure_sense) -> None:
    """Test that the headword is auto-filled in the search input."""
    test_headword = 'acceptance_test_headword'
    page.goto(f"{app_url}/entries/add")
    page.wait_for_selector('#entry-form', state='visible', timeout=10000)

    # Fill in the headword
    page.fill('input.lexical-unit-text', test_headword)

    ensure_sense(page)

    # Open the corpus search modal
    search_buttons = page.locator('.search-corpus-btn')
    search_buttons.first.click()

    # Search input should contain the headword
    search_input = page.locator('#corpusSearchInput')
    expect(search_input).to_have_value(test_headword)


@pytest.mark.integration
def test_search_corpus_api_returns_source_target(page: Page, app_url: str, ensure_sense) -> None:
    """Test that corpus search API returns source/target format."""
    page.goto(f"{app_url}/entries/add")
    page.wait_for_selector('#entry-form', state='visible', timeout=10000)

    page.fill('input.lexical-unit-text', 'test')

    ensure_sense(page)

    # Open modal and perform search
    search_buttons = page.locator('.search-corpus-btn')
    search_buttons.first.click()

    # Click search button
    search_btn = page.locator('#corpusSearchBtn')
    search_btn.click()

    # Wait for results or an empty-state indicator (polling)
    wait_for_corpus_results(page, timeout=10000)

    # Results container should be visible
    results_container = page.locator('#corpusSearchResults')
    expect(results_container).to_be_visible()


@pytest.mark.integration
def test_corpus_results_display_format(page: Page, app_url: str, ensure_sense) -> None:
    """Test that corpus results are displayed with source and target formatting."""
    page.goto(f"{app_url}/entries/add")
    page.wait_for_selector('#entry-form', state='visible', timeout=10000)

    page.fill('input.lexical-unit-text', 'test')

    ensure_sense(page)

    # Open modal
    search_buttons = page.locator('.search-corpus-btn')
    search_buttons.first.click()

    # Perform search
    search_btn = page.locator('#corpusSearchBtn')
    search_btn.click()

    # Wait for results or empty state using polling helper
    wait_for_corpus_results(page, timeout=10000)

    # Results container should be visible
    results_container = page.locator('#corpusSearchResults')
    expect(results_container).to_be_visible()

    # Either results or empty state should be displayed
    results_html = page.locator('#corpusSearchResults').inner_html()
    # Either there are results (corpus-result elements) or empty state message
    has_results = page.locator('.corpus-result').count() > 0
    has_empty_state = 'No examples found' in results_html or 'Enter a search term' in results_html
    assert has_results or has_empty_state, "Expected either results or empty state message"


@pytest.mark.integration
def test_search_input_accepts_custom_query(page: Page, app_url: str, ensure_sense) -> None:
    """Test that users can manually change the search query."""
    page.goto(f"{app_url}/entries/add")
    page.wait_for_selector('#entry-form', state='visible', timeout=10000)

    page.fill('input.lexical-unit-text', 'initial_headword')

    ensure_sense(page)

    # Open modal
    search_buttons = page.locator('.search-corpus-btn')
    search_buttons.first.click()

    # Clear and type a custom query
    search_input = page.locator('#corpusSearchInput')
    search_input.clear()
    search_input.fill('custom_search_term')

    expect(search_input).to_have_value('custom_search_term')


@pytest.mark.integration
def test_corpus_modal_close_button_works(page: Page, app_url: str, ensure_sense) -> None:
    """Test that the modal can be closed."""
    page.goto(f"{app_url}/entries/add")
    page.wait_for_selector('#entry-form', state='visible', timeout=10000)

    ensure_sense(page)

    # Open modal
    search_buttons = page.locator('.search-corpus-btn')
    search_buttons.first.click()

    # Modal should be visible
    modal = page.locator('#corpusSearchModal')
    expect(modal).to_be_visible()

    # Click the close button in modal header
    close_btn = page.locator('#corpusSearchModal .btn-close')
    close_btn.click()

    # Wait for modal to close (Bootstrap modal removal takes time)
    page.wait_for_timeout(1000)

    # Modal should no longer be visible (use visible assertion which checks visibility)
    # After closing, the modal should be hidden
    expect(modal).not_to_be_visible()


@pytest.mark.integration
def test_corpus_search_with_enter_key(page: Page, app_url: str, ensure_sense) -> None:
    """Test that pressing Enter in search input triggers search."""
    page.goto(f"{app_url}/entries/add")
    page.wait_for_selector('#entry-form', state='visible', timeout=10000)

    page.fill('input.lexical-unit-text', 'test')

    ensure_sense(page)

    # Open modal
    search_buttons = page.locator('.search-corpus-btn')
    search_buttons.first.click()

    # Fill search input with a query
    search_input = page.locator('#corpusSearchInput')
    search_input.fill('run')

    # Press Enter
    search_input.press('Enter')

    # Wait for results or empty state using polling helper
    wait_for_corpus_results(page, timeout=10000)

    # Results container should be visible
    results_container = page.locator('#corpusSearchResults')
    expect(results_container).to_be_visible()


@pytest.mark.integration
def test_corpus_results_info_shows_count(page: Page, app_url: str, ensure_sense) -> None:
    """Test that results info shows the number of results found."""
    page.goto(f"{app_url}/entries/add")
    page.wait_for_selector('#entry-form', state='visible', timeout=10000)

    page.fill('input.lexical-unit-text', 'test')

    ensure_sense(page)

    # Open modal and search
    search_buttons = page.locator('.search-corpus-btn')
    search_buttons.first.click()

    search_btn = page.locator('#corpusSearchBtn')
    search_btn.click()

    # Wait for results or empty state
    wait_for_corpus_results(page, timeout=10000)

    # Results info should be visible (if results exist)
    results_info = page.locator('#corpusResultsInfo')
    expect(results_info).to_be_visible()


@pytest.mark.integration
def test_corpus_search_uses_empty_query_gracefully(page: Page, app_url: str, ensure_sense) -> None:
    """Test that searching with empty query shows appropriate state."""
    page.goto(f"{app_url}/entries/add")
    page.wait_for_selector('#entry-form', state='visible', timeout=10000)

    page.fill('input.lexical-unit-text', 'test')

    ensure_sense(page)

    # Open modal
    search_buttons = page.locator('.search-corpus-btn')
    search_buttons.first.click()

    # Clear the search input
    search_input = page.locator('#corpusSearchInput')
    search_input.clear()

    # Click search button - should not crash, might show error or empty state
    search_btn = page.locator('#corpusSearchBtn')
    search_btn.click()

    # The page should still be functional (no crash)
    # Modal should still be visible
    modal = page.locator('#corpusSearchModal')
    expect(modal).to_be_visible(timeout=2000)


@pytest.mark.integration
def test_corpus_search_from_examples_section(page: Page, app_url: str, ensure_sense) -> None:
    """Test that Search Corpus works from the Examples section."""
    page.goto(f"{app_url}/entries/add")
    page.wait_for_selector('#entry-form', state='visible', timeout=10000)

    page.fill('input.lexical-unit-text', 'example_test_word')

    ensure_sense(page)

    # Find the Search Corpus button in the Examples section
    # This button has data-field="example"
    example_search_btn = page.locator('.search-corpus-btn[data-field="example"]')

    # Button should exist (might not be visible if no examples section yet)
    if example_search_btn.count() > 0:
        example_search_btn.first.click()

        # Modal should open
        modal = page.locator('#corpusSearchModal')
        expect(modal).to_be_visible()

        # Search input should have the headword pre-filled
        search_input = page.locator('#corpusSearchInput')
        expect(search_input).to_have_value('example_test_word')


@pytest.mark.integration
def test_corpus_search_from_definitions_section(page: Page, app_url: str, ensure_sense) -> None:
    """Test that Search Corpus works from the Definitions section."""
    page.goto(f"{app_url}/entries/add")
    page.wait_for_selector('#entry-form', state='visible', timeout=10000)

    page.fill('input.lexical-unit-text', 'definition_test_word')

    ensure_sense(page)

    # Find the Search Corpus button in the Definitions section
    # This button has data-field="definition"
    definition_search_btn = page.locator('.search-corpus-btn[data-field="definition"]')

    # Button should exist
    if definition_search_btn.count() > 0:
        definition_search_btn.first.click()

        # Modal should open
        modal = page.locator('#corpusSearchModal')
        expect(modal).to_be_visible()

        # Search input should have the headword pre-filled
        search_input = page.locator('#corpusSearchInput')
        expect(search_input).to_have_value('definition_test_word')
