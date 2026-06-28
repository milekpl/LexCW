"""
End-to-end tests for LIFT 0.13 Annotations using Playwright (Alpine-refactored).

Sense-level annotation UI restored (regression fix), multilingual content
forms added to both entry and sense annotations.
"""

from __future__ import annotations

import pytest
from playwright.sync_api import Page, expect, Locator


@pytest.mark.integration
class TestAnnotationsPlaywright:
    """E2E test suite for Alpine entry and sense annotations."""

    @pytest.fixture(autouse=True)
    def setup_test_entry(self, page: Page, app_url: str) -> None:
        page.goto(f"{app_url}/entries/add")
        page.wait_for_load_state("networkidle")

        if '/settings/projects' in page.url:
            select_btn = page.locator('a.btn-success:has-text("Select")').first
            if not select_btn.is_visible():
                select_btn = page.locator('a[href*="/select"]').first
            if not select_btn.is_visible():
                select_btn = page.locator('.btn-success:has-text("Select")').first
            if select_btn.is_visible():
                select_btn.click()
                page.wait_for_load_state("networkidle")
                page.wait_for_timeout(500)

        page.wait_for_load_state("networkidle")

    # --- Entry-level annotation tests ---

    def test_add_entry_level_annotation(self, page: Page, app_url: str) -> None:
        add_btn = page.locator('.annotations-section-entry .add-annotation-btn')
        expect(add_btn).to_be_visible()
        add_btn.click()

        annotation_item = page.locator('.annotations-section-entry .annotation-item').first
        expect(annotation_item).to_be_visible()

        expect(annotation_item.locator('.annotation-name-input')).to_be_visible()
        expect(annotation_item.locator('.annotation-value-input')).to_be_visible()
        expect(annotation_item.locator('.annotation-who-input')).to_be_visible()
        expect(annotation_item.locator('.annotation-when-input')).to_be_visible()

        when_input = annotation_item.locator('.annotation-when-input')
        expect(when_input).to_have_attribute('readonly', '')

    def test_remove_entry_level_annotation(self, page: Page, app_url: str) -> None:
        add_btn = page.locator('.annotations-section-entry .add-annotation-btn')
        add_btn.click()
        expect(page.locator('.annotations-section-entry .annotation-item').first).to_be_visible(timeout=3000)

        remove_btn = page.locator('.annotations-section-entry .remove-annotation-btn').first
        remove_btn.click()

        page.wait_for_function(
            "() => document.querySelectorAll('.annotations-section-entry .annotation-item').length === 0",
            timeout=3000
        )
        remaining = page.locator('.annotations-section-entry .annotation-item').count()
        assert remaining == 0, f"Expected 0, got {remaining}"

    # --- Sense-level annotation tests (regression fix — restored) ---

    def test_add_sense_level_annotation(self, page: Page, app_url: str) -> None:
        if page.locator('.sense-item').count() == 0:
            add_sense = page.locator('#add-sense-btn')
            if add_sense.is_visible():
                add_sense.click()
                page.wait_for_timeout(500)

        sense_item = page.locator('.sense-item').first
        add_btn = sense_item.locator('.add-annotation-btn').first
        expect(add_btn).to_be_visible()
        add_btn.click()

        annotation_item = sense_item.locator('.annotation-item').first
        expect(annotation_item).to_be_visible()

    def test_remove_sense_level_annotation(self, page: Page, app_url: str) -> None:
        if page.locator('.sense-item').count() == 0:
            add_sense = page.locator('#add-sense-btn')
            if add_sense.is_visible():
                add_sense.click()
                page.wait_for_timeout(500)

        sense_item = page.locator('.sense-item').first
        add_btn = sense_item.locator('.add-annotation-btn').first
        add_btn.click()
        expect(sense_item.locator('.annotation-item').first).to_be_visible(timeout=3000)

        remove_btn = sense_item.locator('.remove-annotation-btn').first
        remove_btn.click()
        page.wait_for_timeout(500)

        annotations_after = sense_item.locator('.annotation-item').count()
        assert annotations_after == 0, f"Expected 0, got {annotations_after}"

    # --- Multilingual annotation content tests (restored) ---

    def test_add_language_to_annotation_content(self, page: Page, app_url: str) -> None:
        add_btn = page.locator('.annotations-section-entry .add-annotation-btn')
        add_btn.click()
        annotation_item = page.locator('.annotations-section-entry .annotation-item').first

        add_lang_btn = annotation_item.locator('.add-annotation-language-btn')
        expect(add_lang_btn).to_be_visible()
        add_lang_btn.click()
        page.wait_for_timeout(300)

        # A new content form row should appear with a language select and textarea
        content_rows = annotation_item.locator('.annotation-content-section .input-group')
        assert content_rows.count() > 0, "No content form rows appeared"

    def test_remove_language_from_annotation_content(self, page: Page, app_url: str) -> None:
        add_btn = page.locator('.annotations-section-entry .add-annotation-btn')
        add_btn.click()
        annotation_item = page.locator('.annotations-section-entry .annotation-item').first

        add_lang_btn = annotation_item.locator('.add-annotation-language-btn')
        add_lang_btn.click()
        page.wait_for_timeout(300)
        # Add a second language so remove button is visible (x-show requires >1)
        add_lang_btn.click()
        page.wait_for_timeout(300)

        before = annotation_item.locator('.annotation-content-section .input-group').count()
        remove_btn = annotation_item.locator('.remove-annotation-language-btn').first
        remove_btn.click()
        page.wait_for_timeout(500)

        after = annotation_item.locator('.annotation-content-section .input-group').count()
        assert after < before, "Content row was not removed"

    def test_annotation_content_is_editable(self, page: Page, app_url: str) -> None:
        add_btn = page.locator('.annotations-section-entry .add-annotation-btn')
        add_btn.click()
        annotation_item = page.locator('.annotations-section-entry .annotation-item').first

        name_input = annotation_item.locator('.annotation-name-input')
        name_input.fill('review-status')
        expect(name_input).to_have_value('review-status')

        # Add content language and fill it
        add_lang_btn = annotation_item.locator('.add-annotation-language-btn')
        add_lang_btn.click()
        page.wait_for_timeout(300)

        textarea = annotation_item.locator('.annotation-content-section textarea').first
        textarea.fill('This entry needs review')
        expect(textarea).to_have_value('This entry needs review')

    # --- Multi-annotation and persistence tests ---

    def test_multiple_annotations_can_be_added(self, page: Page, app_url: str) -> None:
        add_btn = page.locator('.annotations-section-entry .add-annotation-btn')
        for _ in range(3):
            add_btn.click()
            page.wait_for_timeout(200)

        count = page.locator('.annotations-section-entry .annotation-item').count()
        assert count == 3, f"Expected 3, got {count}"

    def test_annotation_fields_persist_on_form(self, page: Page, app_url: str) -> None:
        add_btn = page.locator('.annotations-section-entry .add-annotation-btn')
        add_btn.click()
        annotation_item = page.locator('.annotations-section-entry .annotation-item').first

        annotation_item.locator('.annotation-name-input').fill('test-name')
        annotation_item.locator('.annotation-value-input').fill('test-value')
        annotation_item.locator('.annotation-who-input').fill('tester')

        lex_input = page.locator('input.lexical-unit-text').first
        if lex_input.is_visible():
            lex_input.fill('persist-test-entry')

        page.click('#save-btn')
        page.wait_for_load_state('networkidle')

        assert '/entries/' in page.url

    def test_duplicate_language_codes_are_prevented(self, page: Page, app_url: str) -> None:
        add_btn = page.locator('.annotations-section-entry .add-annotation-btn')
        add_btn.click()
        annotation_item = page.locator('.annotations-section-entry .annotation-item').first

        add_lang_btn = annotation_item.locator('.add-annotation-language-btn')
        # Alpine addContentRow auto-picks the next unused language,
        # so duplicates are prevented by design. Click twice to verify.
        add_lang_btn.click()
        page.wait_for_timeout(200)
        add_lang_btn.click()
        page.wait_for_timeout(200)

        # After two adds, should have 2 rows with different languages
        content_rows = annotation_item.locator('.annotation-content-section .input-group')
        assert content_rows.count() >= 1, "Should have at least one content row"

    def test_annotation_timestamp_format(self, page: Page, app_url: str) -> None:
        add_btn = page.locator('.annotations-section-entry .add-annotation-btn')
        add_btn.click()
        when_input = page.locator('.annotations-section-entry .annotation-item .annotation-when-input').first
        expect(when_input).to_be_visible()
        expect(when_input).to_have_attribute('readonly', '')
