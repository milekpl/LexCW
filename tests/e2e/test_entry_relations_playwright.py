"""
Playwright-based E2E test for entry complex components and variants relations.

This test ensures that complex form components and variants are properly
persisted in the correct UI sections and not leaked into generic relations.

Ported from JavaScript test in e2e/tests/entry_relations.spec.js
"""

from __future__ import annotations

import time
import requests
from typing import Any, Dict
from playwright.sync_api import Page, expect
import pytest


def get_base_url(base_url_from_fixture: str) -> str:
    """Resolve base URL consistently with Playwright config / env."""
    return base_url_from_fixture or 'http://127.0.0.1:5000'


def get_entry(base_url: str, entry_id: str) -> Dict[str, Any]:
    """Load entry via API for server-side verification."""
    response = requests.get(f"{base_url}/api/entries/{entry_id}")
    assert response.ok, f"Failed to get entry {entry_id}: {response.text}"
    return response.json()


@pytest.mark.integration
@pytest.mark.playwright
def test_entry_complex_components_and_variants_persist_in_correct_sections(
    page: Page, app_url: str, e2e_dict_service
) -> None:
    """
    E2E regression for entry-level complex form/component relations.

    Scenario:
    1. Use existing sample entries A and B from the test database.
    2. Create a complex entry C via the HTML entry form that:
       - Adds A as a complex component via the "Complex Form Components" UI
       - Adds B as a variant via the "Variants" UI
    3. Save the form.
    4. Re-open entry C's edit form and verify:
       - The component relation(s) appear under the Complex Form Components card
       - The variant relation(s) appear under the Variants card
       - No _component-lexeme relations are rendered in the generic Relations box
    """
    base_url = get_base_url(app_url)

    # We'll create required sample entries (component, variant) via the UI so they exist in the same test DB
    timestamp = str(int(time.time() * 1000))
    complex_entry_id = f"e2e_complex_{timestamp}"

    def create_simple_entry(headword: str):
        page.goto(f"{base_url}/entries/add")
        page.wait_for_selector('#entry-form')
        page.fill('input.lexical-unit-text', headword)
        # Ensure there is a sense by clicking the appropriate add sense button if necessary
        if page.locator('textarea[name*="definition"]:visible').count() == 0:
            if page.locator('#add-first-sense-btn').count() > 0 and page.locator('#add-first-sense-btn').first.is_visible():
                page.click('#add-first-sense-btn')
            elif page.locator('#add-sense-btn').count() > 0 and page.locator('#add-sense-btn').first.is_visible():
                page.click('#add-sense-btn')
            else:
                generic = page.locator('.add-sense-btn, button:has-text("Add Another Sense"), button:has-text("Add Sense")')
                if generic.count() > 0 and generic.first.is_visible():
                    generic.first.click()
                else:
                    raise RuntimeError('Could not find any Add Sense button on page to create a sense')

            # Wait for visible definition textarea
            for _ in range(50):
                if page.locator('textarea[name*="definition"]:visible').count() > 0:
                    break
                page.wait_for_timeout(100)
            else:
                raise RuntimeError('Timed out waiting for visible definition textarea to appear')

        # Fill visible definition
        page.locator('textarea[name*="definition"]:visible').first.fill(f"{headword} entry")
        # Save
        page.click('button:has-text("Save Entry"), button:has-text("Save")')
        page.wait_for_load_state('networkidle')

    # Create the sample entries used as component and variant targets
    create_simple_entry('component')
    create_simple_entry('variant')

    # --- Act 1: open Add New Entry form and create complex entry via UI ---
    # Entries list is at /entries; "Add New Entry" typically links to /entries/add
    page.goto(f"{base_url}/entries")

    # Click on Add New Entry (button or link). Use text selector to avoid brittle IDs.
    add_entry_selector = 'text="Add New Entry"'
    page.click(add_entry_selector)

    # We should now be on the entry form; fill minimal lexical unit so save is allowed.
    page.wait_for_selector('#entry-form')

    # The lexical unit source language field is required; target the first input.
    headword_input = page.locator('.lexical-unit-forms input.lexical-unit-text').first
    headword_input.fill(f"complex-{timestamp}")

    # Optionally set citation form to make the entry easier to identify in search results
    page.fill('#citation-form', f"complex-entry-{timestamp}")

    # --- Add a complex form component using the UI section ---
    # 1) Choose a component type from the dynamic complex-form-type select
    component_type_select = page.locator('#new-component-type')
    component_type_select.wait_for()

    # Ensure component type is selected (avoid interacting with Select2 UI which can be flaky)
    # Try picking an existing non-empty option; if none, inject a test option and set it
    val = page.locator('#new-component-type').evaluate("el => { const opts = Array.from(el.options).map(o => o.value).filter(Boolean); return opts.length ? opts[0] : null }")
    if val:
        page.select_option('#new-component-type', val)
    else:
        page.evaluate("""() => {
            const sel = document.querySelector('#new-component-type');
            if (sel) {
                const opt = document.createElement('option');
                opt.value = 'test-type';
                opt.text = 'test-type';
                sel.appendChild(opt);
                sel.value = 'test-type';
                sel.dispatchEvent(new Event('change'));
            }
        }""")
        page.wait_for_timeout(200)

    # Wait for the underlying select to have a non-empty value (Select2 can be async)
    for _ in range(50):
        val = page.locator('#new-component-type').evaluate('el => el.value')
        if val:
            break
        page.wait_for_timeout(100)
    else:
        # Try clicking the first option again in case the click didn't register
        page.locator('.select2-results__option').first.click()
        for _ in range(30):
            val = page.locator('#new-component-type').evaluate('el => el.value')
            if val:
                break
            page.wait_for_timeout(100)
        else:
            raise AssertionError('Component type select did not receive a value after opening Select2 and retrying')

    # 2) Search for the base component entry by headword text
    page.fill('#component-search-input', "component")
    page.click('#component-search-btn')
    page.wait_for_timeout(300)  # Give time for the server-side search to populate results

    # Search results container for components
    component_results = page.locator('#component-search-results')
    component_results.wait_for(state='visible')

    # Click the first visible result (which should correspond to our component entry)
    first_component_result = component_results.locator(
        '.entry-result-item:visible, .search-result-item:visible, .list-group-item:visible'
    ).first
    expect(first_component_result).to_be_visible(timeout=10000)
    first_component_result.click()

    # After selecting, the new component should appear in #new-components-container
    new_components_container = page.locator('#new-components-container')
    expect(new_components_container).to_contain_text("component", timeout=10000)

    # After selecting, the new component should appear in #new-components-container
    new_components_container = page.locator('#new-components-container')
    expect(new_components_container).to_contain_text("component")

    # --- Add a variant relation using the Variants UI section ---
    # Create a new blank variant block
    page.click('#add-variant-btn')

    # The new variant item should appear; we target the last .variant-item
    variant_items = page.locator('.variant-item')
    expect(variant_items).to_have_count(1)

    variant_item = variant_items.last

    # Select variant type from its dynamic-lift-range select
    variant_type_select = variant_item.locator('select[data-range-id="variant-type"]')
    variant_type_select.wait_for()

    # Click the Select2 trigger in the variant item
    variant_trigger = variant_item.locator('.select2-selection')
    variant_trigger.click()
    page.wait_for_selector('.select2-results__options')
    # Click the first option
    page.locator('.select2-results__option').first.click()

    # Use the variant search interface to connect to variantTargetEntryId
    variant_search_input = variant_item.locator('input.variant-search-input')
    variant_search_button = variant_item.locator('button.variant-search-btn')

    variant_search_input.fill("variant")
    variant_search_button.click()

    variant_results = page.locator('#variant-search-results-0')
    variant_results.wait_for(state='visible')

    first_variant_result = variant_results.locator('.search-result-item, .list-group-item').first
    first_variant_result.click()

    # Basic smoke check that the variant UI shows the chosen target
    expect(variant_item).to_contain_text("variant")

    # --- Save the entry via the form submit button ---
    # Try a generic save button selector commonly used: text "Save Entry"
    save_button = page.locator(
        'button:has-text("Save Entry"), button:has-text("Save")'
    ).first
    save_button.click()

    # Wait for navigation or success indicator – assume redirect back to entries list or view
    page.wait_for_load_state('networkidle')

    # --- Verify via API that C exists and capture its id (may be auto-generated) ---
    # If server overwrote id, we still expect `complexEntryId` or some entry
    # containing our headword.
    final_complex_id = complex_entry_id

    # Attempt to get by explicit id first; if 404, search via /api/search
    complex_entry = None
    try:
        complex_entry = get_entry(base_url, complex_entry_id)
    except AssertionError:
        # Fallback: use search by headword text to resolve actual stored id
        search_response = requests.get(f"{base_url}/api/search?q=complex-{timestamp}&limit=5")
        assert search_response.ok, f"Search failed: {search_response.text}"
        data = search_response.json()
        found = None
        for entry in data.get('entries', []):
            if entry.get('lexical_unit') and (
                (entry['lexical_unit'].get('en') == f"complex-{timestamp}") or
                f"complex-{timestamp}" in str(entry['lexical_unit'])
            ):
                found = entry
                break
        assert found, f"Could not find complex entry with headword complex-{timestamp}"
        final_complex_id = found['id']
        complex_entry = found

    assert final_complex_id

    # Sanity check: relations in raw JSON should include component/variant relations
    # but we primarily validate placement in the rendered form.

    # --- Act 2: reopen the complex entry form and assert UI placement ---
    page.goto(f"{base_url}/entries/{final_complex_id}/edit")
    page.wait_for_selector('#entry-form')

    # 1) Complex Form Components card should list our component entry
    components_section = page.locator('div.card:has-text("Complex Form Components")')
    expect(components_section).to_contain_text("Complex Form Components")
    expect(components_section).to_contain_text("component")

    # 2) Variants card should list our variant target entry
    variants_section = page.locator('div.variants-section')
    expect(variants_section).to_contain_text("Variants")
    expect(variants_section).to_contain_text("variant")

    # 3) Generic Relations box should NOT show any _component-lexeme relation rows
    relations_section = page.locator('div.relations-section')
    expect(relations_section).to_contain_text("Relations")

    # Ensure that no relation row in this box contains the component headword text
    # If the bug regresses, the component relation might leak into this box.
    relations_text = relations_section.text_content()
    assert "component" not in relations_text

    # Additionally, ensure that no visible relation-item card in this box mentions _component-lexeme
    relation_items = relations_section.locator('.relation-item')
    count = relation_items.count()
    for i in range(count):
        txt = relation_items.nth(i).text_content()
        assert "_component-lexeme" not in txt
