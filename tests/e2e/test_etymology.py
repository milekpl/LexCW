"""
E2E Tests for Etymology Type Population
==========================================

Tests that the etymology type dropdown is correctly populated from LIFT ranges API.
This ensures lexicographers can select appropriate etymological categories when
editing dictionary entries.

Usage:
    pytest tests/e2e/test_etymology.py -v
"""

import pytest
from playwright.sync_api import expect


@pytest.mark.e2e
class TestEtymologyTypePopulation:
    """Test that etymology type dropdown is populated from LIFT ranges."""

    def test_etymology_type_dropdown_populated(self, page, app_url):
        """
        Verify etymology type dropdown contains values from the 'etymology' range.

        Steps:
            1. Navigate to entry form
            2. Click 'Add Etymology' button
            3. Verify type dropdown has values (inheritance, borrowing, compound, etc.)
        """
        # Navigate to create new entry
        page.goto(f"{app_url}/entries/add")
        page.wait_for_load_state('networkidle')

        # Wait for etymology section to be visible
        page.wait_for_selector('#etymology-container', state='visible')
        page.wait_for_selector('#add-etymology-btn', state='visible')

        # Click 'Add Etymology' button
        add_button = page.locator('#add-etymology-btn')
        expect(add_button).to_be_visible()
        add_button.click()

        # Wait for etymology form to appear
        page.wait_for_selector('.etymology-form-item', state='visible')

        # Find the type dropdown
        type_select = page.locator('.etymology-type-select').first
        expect(type_select).to_be_visible()

        # Wait for dynamic range options to load (populated asynchronously)
        page.wait_for_selector('.etymology-type-select option:not([value=""])', state='attached', timeout=10000)

        # Get all options
        options = type_select.locator('option').all_text_contents()

        # Verify expected etymology types are present (from LIFT ranges)
        expected_types = ['borrowed', 'proto']
        for etype in expected_types:
            assert any(etype in opt.lower() for opt in options), \
                f"Etymology type '{etype}' not found in dropdown options: {options}"

        print(f"✅ Etymology type dropdown populated with {len(options)} options")

    def test_etymology_type_selection_works(self, page, app_url):
        """
        Verify selected etymology type can be selected in the dropdown.

        (Save/redirect is tested separately in form save tests.
        This test focuses on the dropdown selection UI.)
        """
        # Create new entry
        page.goto(f"{app_url}/entries/add")
        page.wait_for_load_state('networkidle')

        # Fill basic entry data
        page.fill('input.lexical-unit-text', 'testword')

        # Add etymology
        page.click('#add-etymology-btn')
        page.wait_for_selector('.etymology-form-item', state='visible')

        # Wait for dynamic range options to load
        page.wait_for_selector('.etymology-type-select option:not([value=""])', state='attached', timeout=10000)
        # Select 'borrowed' type by label
        page.select_option('.etymology-type-select', label='borrowed')

        # Verify the selection was made
        selected_value = page.evaluate(
            "document.querySelector('.etymology-type-select')?.value"
        )
        assert selected_value, "No etymology type was selected"
        print(f"✅ Etymology type selected: {selected_value}")

        # Also verify source and form fields can be filled
        # (formForms/glossForms start empty; add a language row first)
        page.fill('.etymology-source-input', 'Latin')
        page.locator('.etymology-form-section .add-etymology-lang-btn').first.click()
        page.wait_for_timeout(300)
        page.fill('.etymology-form-text-input', 'testum')
        source = page.input_value('.etymology-source-input')
        assert source == 'Latin', "Source language field not filled correctly"
        print("✅ Etymology form fields work correctly")


@pytest.mark.e2e
class TestEtymologyRoundtrip:
    """Test that etymology survives a save → reload cycle (§13 round-trip)."""

    def test_etymology_roundtrip(self, page, app_url):
        """
        Add etymology → select type → fill form/gloss → save → reload XML →
        assert <etymology type="…" source="…"> with <form lang><gloss lang>.
        Also asserts exactly one .etymology-form-item (no legacy duplicates).
        """
        import requests
        import time
        import re

        base_url = app_url
        timestamp = str(int(time.time() * 1000))
        headword = f"etym-roundtrip-{timestamp}"

        # ── Create entry with etymology ────────────────────────────────────
        page.goto(f"{base_url}/entries/add")
        page.wait_for_load_state("networkidle")

        page.fill("input.lexical-unit-text", headword)

        # Ensure a sense exists so save doesn't fail
        if page.locator("textarea.definition-text:visible").count() == 0:
            page.click("#add-sense-btn")
            for _ in range(50):
                if page.locator("textarea.definition-text:visible").count() > 0:
                    break
                page.wait_for_timeout(100)
        page.locator("textarea.definition-text:visible").first.fill("Etymology roundtrip definition")

        # Add etymology — should produce exactly one .etymology-form-item
        page.wait_for_selector("#add-etymology-btn", state="visible")
        page.click("#add-etymology-btn")
        page.wait_for_selector(".etymology-form-item", state="visible")

        form_item_count = page.locator(".etymology-form-item").count()
        assert form_item_count == 1, f"Expected exactly 1 .etymology-form-item, found {form_item_count}"

        # Wait for type dropdown options to load
        page.wait_for_selector('.etymology-type-select option:not([value=""])', state="attached", timeout=10000)

        # Select etymology type
        page.select_option(".etymology-type-select", label="borrowed")

        # Fill source
        page.fill(".etymology-source-input", "Latin")

        # Add a form language and fill it
        page.click(".add-etymology-lang-btn")  # adds an empty row to formForms
        page.wait_for_timeout(200)
        page.fill(".etymology-form-text-input", "dictum")

        # Add a gloss language and fill it
        # The first add-lang button is for form, the second for gloss
        page.click(".etymology-gloss-section .add-etymology-lang-btn")
        page.wait_for_timeout(200)
        page.fill(".etymology-gloss-text-input", "said")

        # ── Save ────────────────────────────────────────────────────────────
        page.wait_for_timeout(800)
        try:
            page.wait_for_load_state("networkidle", timeout=10000)
        except Exception:
            pass

        # Save — redirects to view page
        page.wait_for_timeout(800)
        with page.expect_navigation(wait_until="networkidle", timeout=20000):
            page.evaluate("() => submitForm()")
        current_url = page.url
        print(f"DEBUG URL after save: {current_url}")

        # Extract entry ID from the redirect URL
        import re as _re
        m = _re.search(r'/entries/([^/?]+)', current_url)
        entry_id = m.group(1) if m else None
        assert entry_id, f"Could not extract entry ID from URL: {current_url}"

        # ── Verify etymology in saved XML ───────────────────────────────────
        # The entry_id may have a temp- prefix; use the save redirect URL to
        # navigate to the edit page correctly
        print(f"DEBUG entry_id={entry_id}, base={base_url}")
        edit_url = f"{base_url}/entries/{entry_id}/edit"
        print(f"DEBUG navigating to {edit_url}")
        page.goto(edit_url, wait_until="networkidle")
        print(f"DEBUG current URL: {page.url}")

        xml_resp = requests.get(f"{base_url}/api/xml/entries/{entry_id}")
        assert xml_resp.ok, f"Failed to get XML for {entry_id}"
        xml_text = xml_resp.text

        # Assert <etymology> element with type and source
        assert '<etymology' in xml_text, "Etymology element not found in saved XML"
        assert 'type="borrowed"' in xml_text or 'type="borrowing"' in xml_text, (
            f"Expected type in etymology, XML snippet: {xml_text[:800]}"
        )
        assert 'source="Latin"' in xml_text, (
            f"Expected source=\"Latin\" in etymology element"
        )

        # Assert form with language and text
        pattern_form = re.compile(
            r'<form\s+lang="[^"]+"\s*>\s*<text[^>]*>dictum</text>', re.DOTALL
        )
        assert pattern_form.search(xml_text), (
            f"Expected <form lang=...><text>dictum</text> in XML"
        )

        # Assert gloss with language and text
        pattern_gloss = re.compile(
            r'<gloss\s+lang="[^"]+"\s*>\s*<text[^>]*>said</text>', re.DOTALL
        )
        assert pattern_gloss.search(xml_text), (
            f"Expected <gloss lang=...><text>said</text> in XML"
        )

        # ── Reload view page and verify count via XML API ───────────────────
        # (The edit form route may not accept temp IDs; use the XML API instead
        # to confirm the data round-tripped correctly.)

        print("✅ Etymology round-trip: type/ source/ form/ gloss persisted correctly")


@pytest.mark.e2e
class TestEtymologyIpaValidation:
    """Test real-time IPA validation in etymology form rows."""

    def test_etymology_form_ipa_row_shows_validation_error(self, page, app_url):
        """
        Verify that etymology form text gets IPA validation feedback when
        the row language is an IPA code (e.g., seh-fonipa).
        """
        page.goto(f"{app_url}/entries/add")
        page.wait_for_load_state("networkidle")

        page.fill("input.lexical-unit-text", "etymology-ipa-validation")

        page.wait_for_selector("#add-etymology-btn", state="visible")
        page.click("#add-etymology-btn")
        page.wait_for_selector(".etymology-form-item", state="visible")

        # Add a form language row and inspect its language code.
        page.locator(".etymology-form-section .add-etymology-lang-btn").first.click()
        page.wait_for_selector(".etymology-form-lang-row", state="visible")

        row = page.locator(".etymology-form-lang-row").first
        lang_select = row.locator(".etymology-form-lang-select")
        options = lang_select.locator("option").all_text_contents()
        ipa_option = None
        for opt in options:
            normalized = opt.strip().lower()
            if "fonipa" in normalized or "ipa" in normalized:
                ipa_option = opt.strip()
                break

        if not ipa_option:
            pytest.skip(
                "Project languages do not expose an IPA code option in etymology language selector"
            )

        lang_select.select_option(label=ipa_option)

        form_input = row.locator(".etymology-form-text-input")

        # Enter an invalid IPA value (digits are invalid in current validator).
        form_input.fill("bad123")
        form_input.blur()
        page.wait_for_timeout(500)

        classes = form_input.evaluate("el => el.className")
        assert "is-invalid" in classes, f"Expected is-invalid class for invalid IPA, got: {classes}"

        # Correct it and verify the error state clears.
        form_input.fill("/ˈbad/")
        form_input.blur()
        page.wait_for_timeout(500)

        classes_after_fix = form_input.evaluate("el => el.className")
        assert "is-invalid" not in classes_after_fix, (
            f"Expected validation error to clear after valid IPA, got: {classes_after_fix}"
        )
