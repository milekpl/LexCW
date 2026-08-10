"""
E2E tests for LIFT 0.13 Custom Fields (Alpine-refactored).

After the Alpine refactor, literal-meaning, exemplar, and scientific-name
use Alpine senseTree addRow/removeRow with x-model textareas.
Selectors updated from legacy class names to Alpine-compatible patterns.
"""

from __future__ import annotations

import pytest
from playwright.sync_api import Page, expect
import re


def _field_container(page: Page, label_text: str):
    """Find the Alpine senseTree field container by label text."""
    return page.locator('.mb-3').filter(has=page.locator(
        f'label:has-text("{label_text}")')).first


def _add_lang_btn(container):
    """Find the 'Add Language' button inside a field container."""
    return container.locator('button:has-text("Add Language")').first


def _textareas_in(container):
    """Find text inputs/areas inside a field container (Alpine x-for rows).
    Alpine uses <input type="text"> for literal-meaning/exemplar/scientific-name,
    and <textarea> for notes. Match both."""
    return container.locator('input[type="text"]:not(.form-select), textarea')


def _remove_btns_in(container):
    """Find remove buttons inside a field container (× buttons from Alpine)."""
    return container.locator('button:has-text("×")')


@pytest.mark.integration
class TestCustomFieldsPlaywright:
    """E2E test suite for Alpine senseTree custom fields."""

    @pytest.fixture(autouse=True)
    def setup_test_entry(self, page: Page, app_url: str) -> None:
        page.goto(f"{app_url}/entries/add")
        page.wait_for_load_state("load")

        lexical_unit = page.locator('input.lexical-unit-text').first
        if lexical_unit.is_visible():
            lexical_unit.fill("test-word")

        add_sense_btn = page.locator('#add-sense-btn')
        if add_sense_btn.is_visible():
            add_sense_btn.click()

        sense_def = page.locator('textarea.definition-text').first
        if sense_def.is_visible():
            sense_def.fill("test definition")

    # --- Literal Meaning ---

    def test_literal_meaning_field_visible(self, page: Page, app_url) -> None:
        page.evaluate("window.scrollTo(0, document.body.scrollHeight)")

        label = page.locator('label').filter(has_text=re.compile(r'Literal Meaning', re.IGNORECASE)).first
        expect(label).to_be_visible()

        container = _field_container(page, 'Literal Meaning')
        add_btn = _add_lang_btn(container)
        expect(add_btn).to_be_visible()

    def test_add_literal_meaning_language(self, page: Page, app_url: str) -> None:
        page.evaluate("window.scrollTo(0, document.body.scrollHeight)")

        page.on('dialog', lambda dialog: dialog.accept('en'))

        container = _field_container(page, 'Literal Meaning')
        before = _textareas_in(container).count()
        _add_lang_btn(container).click()
        expect(_textareas_in(container)).to_have_count(before + 1, timeout=3000)

        # A remove button should appear for the new row
        assert _remove_btns_in(container).count() > 0

    def test_remove_literal_meaning_language(self, page: Page, app_url: str) -> None:
        page.evaluate("window.scrollTo(0, document.body.scrollHeight)")

        # Alpine addRow doesn't use dialog; auto-picks next language
        container = _field_container(page, 'Literal Meaning')
        # Need at least 2 rows for remove button to be visible (x-show)
        _add_lang_btn(container).click()
        _add_lang_btn(container).click()
        expect(_textareas_in(container)).to_have_count(2, timeout=3000)
        before = _textareas_in(container).count()
        page.wait_for_selector('button:has-text("×"):visible', timeout=3000)
        _remove_btns_in(container).first.click()
        expect(_textareas_in(container)).to_have_count(before - 1, timeout=3000)

    def test_fill_literal_meaning_content(self, page: Page, app_url: str) -> None:
        page.evaluate("window.scrollTo(0, document.body.scrollHeight)")

        page.on('dialog', lambda dialog: dialog.accept('en'))

        container = _field_container(page, 'Literal Meaning')
        _add_lang_btn(container).click()

        field = _textareas_in(container).first
        field.fill('sun-flower')
        expect(field).to_have_value('sun-flower')

    # --- Exemplar ---

    def test_exemplar_field_visible_in_sense(self, page: Page, app_url: str) -> None:
        page.evaluate("window.scrollTo(0, document.body.scrollHeight)")

        label = page.locator('label').filter(has_text='Exemplar').first
        expect(label).to_be_visible()

        container = _field_container(page, 'Exemplar')
        expect(_add_lang_btn(container)).to_be_visible()

    def test_add_exemplar_language(self, page: Page, app_url: str) -> None:
        page.evaluate("window.scrollTo(0, document.body.scrollHeight)")

        page.on('dialog', lambda dialog: dialog.accept('en'))

        container = _field_container(page, 'Exemplar')
        before = _textareas_in(container).count()
        _add_lang_btn(container).click()
        expect(_textareas_in(container)).to_have_count(before + 1, timeout=3000)

    def test_remove_exemplar_language(self, page: Page, app_url: str) -> None:
        page.evaluate("window.scrollTo(0, document.body.scrollHeight)")

        page.on('dialog', lambda dialog: dialog.accept('en'))

        container = _field_container(page, 'Exemplar')
        _add_lang_btn(container).click()
        expect(_textareas_in(container)).to_have_count(1, timeout=3000)
        before = _textareas_in(container).count()
        page.wait_for_selector('button:has-text("×"):visible', timeout=3000)
        _remove_btns_in(container).first.click()
        expect(_textareas_in(container)).to_have_count(before - 1, timeout=3000)

    def test_fill_exemplar_content(self, page: Page, app_url: str) -> None:
        page.evaluate("window.scrollTo(0, document.body.scrollHeight)")

        page.on('dialog', lambda dialog: dialog.accept('en'))

        container = _field_container(page, 'Exemplar')
        _add_lang_btn(container).click()

        field = _textareas_in(container).first
        field.fill('mice')
        expect(field).to_have_value('mice')

    # --- Scientific Name ---

    def test_scientific_name_field_visible_in_sense(self, page: Page, app_url: str) -> None:
        page.evaluate("window.scrollTo(0, document.body.scrollHeight)")

        label = page.locator('label').filter(has_text='Scientific Name').first
        expect(label).to_be_visible()

        container = _field_container(page, 'Scientific Name')
        expect(_add_lang_btn(container)).to_be_visible()

    def test_add_scientific_name_language(self, page: Page, app_url: str) -> None:
        page.evaluate("window.scrollTo(0, document.body.scrollHeight)")

        page.on('dialog', lambda dialog: dialog.accept('en'))

        container = _field_container(page, 'Scientific Name')
        before = _textareas_in(container).count()
        _add_lang_btn(container).click()
        expect(_textareas_in(container)).to_have_count(before + 1, timeout=3000)

    def test_remove_scientific_name_language(self, page: Page, app_url: str) -> None:
        page.evaluate("window.scrollTo(0, document.body.scrollHeight)")

        page.on('dialog', lambda dialog: dialog.accept('en'))

        container = _field_container(page, 'Scientific Name')
        _add_lang_btn(container).click()
        expect(_textareas_in(container)).to_have_count(1, timeout=3000)
        before = _textareas_in(container).count()
        page.wait_for_selector('button:has-text("×"):visible', timeout=3000)
        _remove_btns_in(container).first.click()
        expect(_textareas_in(container)).to_have_count(before - 1, timeout=3000)

    def test_fill_scientific_name_content(self, page: Page, app_url: str) -> None:
        page.evaluate("window.scrollTo(0, document.body.scrollHeight)")

        page.on('dialog', lambda dialog: dialog.accept('en'))

        container = _field_container(page, 'Scientific Name')
        _add_lang_btn(container).click()

        field = _textareas_in(container).first
        field.fill('Helianthus annuus')
        expect(field).to_have_value('Helianthus annuus')

    def test_add_multiple_languages_to_literal_meaning(self, page: Page, app_url: str) -> None:
        page.evaluate("window.scrollTo(0, document.body.scrollHeight)")

        langs = iter(['en', 'fr'])
        page.on('dialog', lambda dialog: dialog.accept(next(langs, 'en')))

        container = _field_container(page, 'Literal Meaning')
        btn = _add_lang_btn(container)
        before = _textareas_in(container).count()
        btn.click()
        btn.click()
        expect(_textareas_in(container)).to_have_count(before + 2, timeout=3000)

    def test_all_custom_fields_visible_together(self, page: Page, app_url: str) -> None:
        page.evaluate("window.scrollTo(0, document.body.scrollHeight)")

        for label_text in ['Literal Meaning', 'Exemplar', 'Scientific Name']:
            label = page.locator('label').filter(has_text=re.compile(label_text, re.IGNORECASE)).first
            expect(label).to_be_visible()

    def test_custom_fields_have_help_text(self, page: Page, app_url: str) -> None:
        page.evaluate("window.scrollTo(0, document.body.scrollHeight)")

        for label_text in ['Literal Meaning', 'Exemplar', 'Scientific Name']:
            container = page.locator('.mb-3').filter(has=page.locator(
                f'label:has-text("{label_text}")')).first
            help_text = container.locator('.form-text').first
            expect(help_text).to_be_visible()

    def test_custom_fields_persist_after_add_another_sense(self, page: Page, app_url: str) -> None:
        page.on('dialog', lambda dialog: dialog.accept('en'))

        container = _field_container(page, 'Exemplar')
        _add_lang_btn(container).click()

        field = _textareas_in(container).first
        field.fill('first sense exemplar')

        # Baseline before we add a sense (the add page pre-seeds one sense and the
        # autouse fixture already added another, so the absolute count is fixture-
        # dependent — assert the delta, not a hardcoded total).
        exemplar_labels = page.locator('label').filter(has_text=re.compile(r'Exemplar', re.IGNORECASE))
        before = exemplar_labels.count()

        senses_before = page.locator('.sense-item').count()
        page.locator('#add-sense-btn').click()
        expect(page.locator('.sense-item')).to_have_count(senses_before + 1, timeout=3000)

        sense_defs = page.locator('.sense-item').nth(1).locator('textarea.definition-text')
        if sense_defs.count() > 0:
            sense_defs.first.fill('second definition')

        # Adding a sense adds exactly one more Exemplar section...
        expect(exemplar_labels).to_have_count(before + 1)

        # ...and the first sense's exemplar value survives the re-render (the real point).
        first_field = _textareas_in(_field_container(page, 'Exemplar'))
        expect(first_field).to_have_value('first sense exemplar')
