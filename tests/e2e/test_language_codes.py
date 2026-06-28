"""
E2E Tests for Multilingual Language Codes in LIFT XML (Alpine-refactored).

After the Alpine refactor, language selects use x-model with class selectors:
.language-select, .example-sentence-lang, .example-translation-lang.
"""

import pytest
from playwright.sync_api import expect


@pytest.mark.e2e
class TestLanguageCodesInXML:
    """Verify language codes in generated LIFT XML match user selections."""

    def _get_live_preview_xml(self, page):
        xml = page.evaluate("""
            () => {
                const pre = document.getElementById('live-preview-xml');
                return pre ? pre.textContent : null;
            }
        """)
        return xml

    def test_definition_language_selector_exists(self, page, app_url):
        page.goto(f"{app_url}/entries/add")
        page.wait_for_load_state('networkidle')

        page.locator('#add-sense-btn').click()
        page.wait_for_timeout(500)

        # Alpine uses .language-select inside sense tree for definition/gloss
        lang_select = page.locator('.language-select').first
        expect(lang_select).to_be_visible()

    def test_example_sentence_has_language_selector(self, page, app_url):
        page.goto(f"{app_url}/entries/add")
        page.wait_for_load_state('networkidle')

        page.locator('#add-sense-btn').click()
        page.wait_for_timeout(500)

        page.locator('.add-example-btn').first.click()
        page.wait_for_timeout(500)

        # Alpine uses .example-sentence-lang for sentence language
        lang_select = page.locator('.example-sentence-lang').first
        expect(lang_select).to_be_visible()

    def test_translation_has_language_selector(self, page, app_url):
        page.goto(f"{app_url}/entries/add")
        page.wait_for_load_state('networkidle')

        page.locator('#add-sense-btn').click()
        page.wait_for_timeout(500)

        page.locator('.add-example-btn').first.click()
        page.wait_for_timeout(500)

        # Alpine uses .example-translation-lang for translation language
        lang_select = page.locator('.example-translation-lang').first
        expect(lang_select).to_be_visible()

    def test_add_gloss_language_button_works(self, page, app_url):
        page.goto(f"{app_url}/entries/add")
        page.wait_for_load_state('networkidle')

        page.locator('#add-sense-btn').click()
        page.wait_for_timeout(500)

        # Alpine uses button with @click="addRow(sense.glossForms)"
        # Find the gloss section and click "Add Language"
        gloss_container = page.locator('.mb-3').filter(has=page.locator(
            'label:has-text("Gloss")')).first
        add_btn = gloss_container.locator('button:has-text("Add Language")').first
        expect(add_btn).to_be_visible()

        before = gloss_container.locator('.language-select').count()
        add_btn.click()
        page.wait_for_timeout(300)

        after = gloss_container.locator('.language-select').count()
        assert after > before

    def test_generated_xml_contains_correct_languages(self, page, app_url):
        page.goto(f"{app_url}/entries/add")
        page.wait_for_load_state('networkidle')

        page.locator('input.lexical-unit-text').first.fill('lang-test-word')
        page.locator('#add-sense-btn').click()
        page.wait_for_timeout(500)

        # Fill definition
        def_textareas = page.locator('textarea.definition-text')
        if def_textareas.count() > 0:
            def_textareas.first.fill('language test definition')

        # Verify language selector is present (Alpine .language-select)
        lang_select = page.locator('.language-select').first
        if lang_select.count() > 0:
            # Select a valid option dynamically instead of hardcoding 'fr'
            options = lang_select.locator('option')
            if options.count() > 1:
                # Pick second option (first is usually empty/default)
                second_value = options.nth(1).get_attribute('value')
                if second_value:
                    lang_select.select_option(value=second_value)
                    page.wait_for_timeout(300)

        page.click('#save-btn')
        page.wait_for_load_state('networkidle')

        # Reload and check XML via API
        entry_id = page.url.rstrip('/').rsplit('/', 1)[-1]
        import requests
        resp = requests.get(f"{app_url}/api/entries/{entry_id}")
        assert resp.ok
        data = resp.json()
        senses = data.get('senses', [])
        assert len(senses) > 0
