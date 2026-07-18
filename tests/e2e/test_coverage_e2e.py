"""
E2E tests for Coverage Checker.

Tests the full coverage checking pipeline through the web UI
using Playwright against a running Flask server.
"""
import re
import pytest
from playwright.sync_api import Page, expect


def test_coverage_page_loads(page: Page, app_url: str) -> None:
    """The coverage page loads and shows tabs."""
    page.goto(f"{app_url}/coverage")
    expect(page).to_have_title(re.compile(r"Coverage Checker"))
    expect(page.get_by_role("tab", name="Resource Coverage")).to_be_visible()
    expect(page.get_by_role("tab", name="Text Coverage")).to_be_visible()
    expect(page.get_by_role("tab", name="Systematicity")).to_be_visible()
    expect(page.get_by_role("tab", name="Sense Alignment")).to_be_visible()
    expect(page.get_by_role("tab", name="WordNet Lookup")).to_be_visible()


def test_wordnet_lookup(page: Page, app_url: str) -> None:
    """WordNet lookup returns synsets for 'bank'."""
    page.goto(f"{app_url}/coverage")

    # Switch to WordNet tab
    page.get_by_role("tab", name="WordNet Lookup").click()

    # Type a word and search
    page.fill("#wordnet-word", "bank")
    page.click("#wordnet-form button[type='submit']")

    # Wait for results
    page.wait_for_selector("#wordnet-results:not(.d-none)")

    # Should show synsets
    expect(page.locator("#wordnet-results-header")).to_contain_text("bank")
    expect(page.locator("#wordnet-results-header")).to_contain_text("synsets")
    # Verify at least one result was returned
    assert page.locator("#wordnet-results-body .list-group-item").count() > 0


def test_text_coverage(page: Page, app_url: str) -> None:
    """Text coverage analysis works."""
    page.goto(f"{app_url}/coverage")

    # Switch to Text Coverage tab
    page.get_by_role("tab", name="Text Coverage").click()

    # Enter text
    page.fill("#text-input", "The cat sat on the mat. A dog ran through the garden.")

    # Submit
    page.click("#text-form button[type='submit']")

    # Wait for results
    page.wait_for_selector("#text-results:not(.d-none)")

    # Should show lemmas
    expect(page.locator("#text-results")).to_be_visible()
    assert page.locator("#text-table-body tr").count() > 0


def test_systematicity_categories(page: Page, app_url: str) -> None:
    """Systematicity tab shows categories."""
    page.goto(f"{app_url}/coverage")

    # Switch to Systematicity tab
    page.get_by_role("tab", name="Systematicity").click()

    # Run checks
    page.click("#run-systematicity")

    # Wait for results
    page.wait_for_selector("#systematicity-results .table", timeout=30000)

    # Should show categories
    expect(page.locator("#systematicity-results .table")).to_be_visible()


def test_resource_coverage_upload(page: Page, app_url: str, tmp_path) -> None:
    """Resource file upload and coverage check."""
    page.goto(f"{app_url}/coverage")

    # Create a test file
    test_file = tmp_path / "test_words.txt"
    test_file.write_text("cat\ndog\nrun\nbank\nhouse\ncar\n")

    # Upload file
    page.set_input_files("#resource-file", str(test_file))

    # Submit
    page.click("#resource-form button[type='submit']")

    # Wait for results
    page.wait_for_selector("#resource-results:not(.d-none)")

    # Should show entries
    assert page.locator("#resource-table-body tr").count() > 0


def test_sense_alignment_tab(page: Page, app_url: str) -> None:
    """Sense alignment tab loads and can run."""
    page.goto(f"{app_url}/coverage")

    # Switch to Sense Alignment tab
    page.get_by_role("tab", name="Sense Alignment").click()

    # Should show controls
    expect(page.locator("#threshold-low")).to_be_visible()
    expect(page.locator("#threshold-high")).to_be_visible()
    expect(page.locator("#run-alignment")).to_be_visible()

    # Run alignment
    page.click("#run-alignment")

    # Wait for results or message
    page.wait_for_selector("#alignment-results:not(.d-none)", timeout=30000)
