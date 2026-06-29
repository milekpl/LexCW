"""
E2E tests for configurable entry view modes.

Tests that the view page correctly filters sections based on
the selected view mode (default / annotations / all).

Mode switching is client-side (instant). All sections are always
in the DOM — only visibility toggles.
"""

from __future__ import annotations

import re
import pytest
from playwright.sync_api import Page, expect


@pytest.mark.integration
@pytest.mark.playwright
def test_entry_view_mode_switcher_visible(page: Page, app_url: str) -> None:
    """The mode switcher pill should be visible on the view page."""
    page.goto(f"{app_url}/entries/test_entry_1")
    page.wait_for_load_state("networkidle")

    read_btn = page.locator('button[data-view-mode="default"]')
    annotate_btn = page.locator('button[data-view-mode="annotations"]')
    all_btn = page.locator('button[data-view-mode="all"]')

    expect(read_btn).to_be_visible()
    expect(annotate_btn).to_be_visible()
    expect(all_btn).to_be_visible()

    # Default mode should have "Read" highlighted (btn-primary)
    expect(read_btn).to_have_class(re.compile(r"btn-primary"))


@pytest.mark.integration
@pytest.mark.playwright
def test_default_mode_hides_structured_senses(page: Page, app_url: str) -> None:
    """Default mode hides the structured senses section."""
    page.goto(f"{app_url}/entries/test_entry_1?view=default")
    page.wait_for_load_state("networkidle")

    # Structured senses section should NOT be visible
    senses_section = page.locator('.card-header h5:has-text("Senses")')
    expect(senses_section).not_to_be_visible()

    # Core sections should be visible
    css_section = page.locator('.card-header h5:has-text("CSS Display")')
    expect(css_section).to_be_visible()

    related_section = page.locator('.card-header h5:has-text("Related")')
    expect(related_section).to_be_visible()


@pytest.mark.integration
@pytest.mark.playwright
def test_all_mode_shows_structured_senses(page: Page, app_url: str) -> None:
    """All mode shows the structured senses view."""
    page.goto(f"{app_url}/entries/test_entry_1?view=all")
    page.wait_for_load_state("networkidle")

    # Structured senses section should be visible
    senses_section = page.locator('.card-header h5:has-text("Senses")')
    expect(senses_section).to_be_visible()

    content = page.content()
    assert 'cat' in content


@pytest.mark.integration
@pytest.mark.playwright
def test_view_mode_session_persistence(page: Page, app_url: str) -> None:
    """View mode should persist in sessionStorage across navigations."""
    page.goto(f"{app_url}/entries/test_entry_1?view=annotations")
    page.wait_for_load_state("networkidle")

    # Navigate to a different entry without mode param
    page.goto(f"{app_url}/entries/test_entry_2")
    page.wait_for_load_state("networkidle")

    # The annotations mode should be active (from sessionStorage)
    annotate_btn = page.locator('button[data-view-mode="annotations"]')
    expect(annotate_btn).to_have_class(re.compile(r"btn-primary"))


@pytest.mark.integration
@pytest.mark.playwright
def test_client_side_mode_switching(page: Page, app_url: str) -> None:
    """Switching modes via buttons should be instant (no page reload)."""
    page.goto(f"{app_url}/entries/test_entry_1?view=default")
    page.wait_for_load_state("networkidle")

    senses_section = page.locator('.card-header h5:has-text("Senses")')
    expect(senses_section).not_to_be_visible()

    # Click "All" button — should show senses instantly
    page.locator('button[data-view-mode="all"]').click()
    expect(senses_section).to_be_visible()

    # Click "Read" — should hide senses again
    page.locator('button[data-view-mode="default"]').click()
    expect(senses_section).not_to_be_visible()


@pytest.mark.integration
@pytest.mark.playwright
def test_annotation_view_mode(page: Page, app_url: str) -> None:
    """
    Annotations mode shows annotation and custom field sections.

    Full round-trip: create entry with annotation → verify visibility per mode.
    """
    import time
    timestamp = str(int(time.time() * 1000))
    headword = f"view-mode-test-{timestamp}"

    # === Step 1: Create entry via form ===
    page.goto(f"{app_url}/entries/add")
    page.wait_for_selector('#entry-form')

    page.fill('input.lexical-unit-text', headword)

    if page.locator('textarea.definition-text:visible').count() == 0:
        page.click('#add-first-sense-btn')
        for _ in range(50):
            if page.locator('textarea.definition-text:visible').count() > 0:
                break
            page.wait_for_timeout(100)
    page.locator('textarea.definition-text:visible').first.fill(f"Definition for {headword}")

    page.click('#save-btn')
    page.wait_for_load_state('networkidle')

    current_url = page.url
    match = re.search(r'/entries/([^/?]+)', current_url)
    assert match, f"Could not extract entry_id from URL: {current_url}"
    entry_id = match.group(1)

    # === Step 2: Open edit form and add an annotation ===
    page.goto(f"{app_url}/entries/{entry_id}/edit")
    page.wait_for_selector('#entry-form')

    add_btn = page.locator('.annotations-section-entry .add-annotation-btn')
    expect(add_btn).to_be_visible()
    add_btn.click()
    page.wait_for_timeout(300)

    annotation_item = page.locator('.annotations-section-entry .annotation-item').first
    annotation_item.locator('.annotation-name-input').fill('review-status')
    annotation_item.locator('.annotation-value-input').fill('pending')
    annotation_item.locator('.annotation-who-input').fill('e2e-tester')

    # === Step 3: Save (redirects to view page) ===
    page.click('#save-btn')
    page.wait_for_load_state('networkidle')
    assert entry_id in page.url

    # Clear sessionStorage to start in default mode
    page.evaluate("sessionStorage.removeItem('entryViewMode')")
    page.reload()
    page.wait_for_load_state("networkidle")

    # === Step 4: Verify default mode hides annotations ===
    annot_section = page.locator('.card-header h5:has-text("Annotations")')
    expect(annot_section).not_to_be_visible()

    # === Step 5: Click Annotate — annotations appear instantly ===
    page.locator('button[data-view-mode="annotations"]').click()
    expect(annot_section).to_be_visible()

    content = page.content()
    assert 'review-status' in content
    assert 'pending' in content
    assert 'e2e-tester' in content

    # === Step 6: Click All — senses visible too ===
    senses_section = page.locator('.card-header h5:has-text("Senses")')
    expect(senses_section).not_to_be_visible()

    page.locator('button[data-view-mode="all"]').click()
    expect(senses_section).to_be_visible()
    expect(annot_section).to_be_visible()
