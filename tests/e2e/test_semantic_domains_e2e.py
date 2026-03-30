"""
E2E tests for semantic domain field functionality.

Tests cover:
1. Single semantic domain selection
2. Multiple semantic domain selection
3. Domain persistence via API
4. Domain display in view page
5. Deselect all domains
6. Full round-trip test
"""

from __future__ import annotations

import time
import requests
import pytest
from typing import Any, Dict
from playwright.sync_api import Page, expect


def get_entry(base_url: str, entry_id: str) -> Dict[str, Any]:
    """Load entry via API for server-side verification."""
    response = requests.get(f"{base_url}/api/entries/{entry_id}")
    assert response.ok, f"Failed to get entry {entry_id}: {response.text}"
    return response.json()


def search_entry(base_url: str, query: str) -> Dict[str, Any]:
    """Search for entries and return results."""
    response = requests.get(f"{base_url}/api/search?q={query}&limit=10")
    assert response.ok, f"Search failed: {response.text}"
    return response.json()


def create_entry_via_api(base_url: str, headword: str, definition: str = "Test definition") -> Dict[str, Any]:
    """Create an entry via API for setup purposes."""
    search = search_entry(base_url, headword)
    if search.get('entries') and len(search['entries']) > 0:
        for entry in search['entries']:
            lu = entry.get('lexical_unit', {})
            if isinstance(lu, dict):
                if any(headword in str(v) for v in lu.values()):
                    return entry
            elif isinstance(lu, str) and headword in lu:
                return entry

    data = {
        "lexical_unit": {"en": headword},
        "senses": [{"definition": {"en": definition}}]
    }
    response = requests.post(f"{base_url}/api/entries/", json=data)
    assert response.ok, f"Failed to create entry: {response.text}"
    return response.json()


def select_semantic_domain(page: Page, index: int = 1) -> None:
    """Select a semantic domain option by directly setting the select value via JavaScript.

    This bypasses the Select2 UI which can be flaky in tests.
    For multi-select, we need to set the selected property on options.
    """
    # Debug: check if select exists and has options
    debug_info = page.evaluate("""() => {
        const selects = document.querySelectorAll('select[data-range-id="semantic-domain-ddp4"]');
        const result = {
            count: selects.length,
            options: [],
            selectedValues: []
        };
        if (selects.length > 0) {
            const sel = selects[0];
            for (let i = 0; i < sel.options.length; i++) {
                result.options.push({value: sel.options[i].value, text: sel.options[i].textContent, selected: sel.options[i].selected});
            }
            for (let i = 0; i < sel.options.length; i++) {
                if (sel.options[i].selected) {
                    result.selectedValues.push(sel.options[i].value);
                }
            }
        }
        return result;
    }""")
    print(f"DEBUG: Semantic domain select info: {debug_info}")

    # Ensure the select has been populated with options (wait for rangesLoader to populate)
    try:
        page.wait_for_function(
            '(idx) => { const sel = document.querySelector("select[data-range-id=\"semantic-domain-ddp4\"]"); return sel && sel.options && sel.options.length > idx + 1; }',
            index,
            timeout=5000,
        )
    except Exception:
        # Force a populate and wait a little
        page.evaluate("""() => {
            const sel = document.querySelector('select[data-range-id="semantic-domain-ddp4"]');
            if (sel && window.rangesLoader) {
                window.rangesLoader.populateSelect(sel, 'semantic-domain-ddp4', { emptyOption: 'Select semantic domain(s)' });
            }
        }""")
        page.wait_for_timeout(500)

    # Use JavaScript to set the select value directly
    page.evaluate("""(idx) => {
        const selects = document.querySelectorAll('select[data-range-id="semantic-domain-ddp4"]');
        if (selects.length > 0) {
            const sel = selects[0];
            // Clear existing selections first
            for (let i = 0; i < sel.options.length; i++) {
                sel.options[i].selected = false;
            }
            // Select the target option by index (skip placeholder at index 0)
            if (sel.options.length > idx + 1) {
                sel.options[idx + 1].selected = true;
            }
            // Dispatch change events to notify any listeners
            sel.dispatchEvent(new Event('change', { bubbles: true }));
            sel.dispatchEvent(new Event('input', { bubbles: true }));
        }
    }""", index)
    page.wait_for_timeout(200)

    # Debug: check selected values after setting
    after_selection = page.evaluate("""() => {
        const selects = document.querySelectorAll('select[data-range-id="semantic-domain-ddp4"]');
        const result = {selectedValues: []};
        if (selects.length > 0) {
            const sel = selects[0];
            for (let i = 0; i < sel.options.length; i++) {
                if (sel.options[i].selected) {
                    result.selectedValues.push(sel.options[i].value);
                }
            }
        }
        return result;
    }""")
    print(f"DEBUG: After selection: {after_selection}")


def select_multiple_semantic_domains(page: Page, indices: list[int]) -> None:
    """Select multiple semantic domain options by setting the select option selections directly.

    Waits for options to be present, retries by triggering the ranges loader if necessary.
    Note: indices may exceed available options; in that case, only valid options are selected.
    """
    max_index = max(indices) if indices else 0
    try:
        page.wait_for_function(
            '(maxIdx) => { const sel = document.querySelector("select[data-range-id=\"semantic-domain-ddp4\"]"); return sel && sel.options && sel.options.length > maxIdx + 1; }',
            max_index,
            timeout=5000,
        )
    except Exception:
        # Try to force a populate if the loader is available
        page.evaluate("""() => {
            const sel = document.querySelector('select[data-range-id="semantic-domain-ddp4"]');
            if (sel && window.rangesLoader) {
                window.rangesLoader.populateSelect(sel, 'semantic-domain-ddp4', { emptyOption: 'Select semantic domain(s)' });
            }
        }""")
        page.wait_for_timeout(500)

    # Set selections (only for indices that exist)
    page.evaluate("""(indices) => {
        const selects = document.querySelectorAll('select[data-range-id="semantic-domain-ddp4"]');
        if (selects.length === 0) return;
        const sel = selects[0];
        for (let i = 0; i < sel.options.length; i++) {
            sel.options[i].selected = false;
        }
        let setCount = 0;
        for (const idx of indices) {
            if (sel.options.length > idx + 1) {
                sel.options[idx + 1].selected = true;
                setCount++;
            }
        }
        // If none of the requested indices were valid, select the first available option as fallback
        if (setCount === 0) {
            for (let i = 1; i < sel.options.length && setCount < (indices.length || 1); i++) {
                if (sel.options[i].value) {
                    sel.options[i].selected = true;
                    setCount++;
                }
            }
        }
        sel.dispatchEvent(new Event('change', { bubbles: true }));
        sel.dispatchEvent(new Event('input', { bubbles: true }));
    }""", indices)
    page.wait_for_timeout(200)

    after = page.evaluate("""() => {
        const sel = document.querySelector('select[data-range-id="semantic-domain-ddp4"]');
        const res = {selected: []};
        if (sel) {
            for (let i = 0; i < sel.options.length; i++) {
                if (sel.options[i].selected) res.selected.push(sel.options[i].value);
            }
        }
        return res;
    }""")
    print(f"DEBUG: After multiple selection: {after}")


def select_first_n_semantic_domains(page: Page, n: int = 2) -> None:
    """Select the first n non-empty semantic domain options.

    Retries until at least n selections are observed or timeout elapses.
    """
    # Ensure the select is populated (allowing rangesLoader to run)
    try:
        page.wait_for_function(
            '(count) => { const sel = document.querySelector("select[data-range-id=\\"semantic-domain-ddp4\\"]"); return sel && sel.options && sel.options.length > count; }',
            n,
            timeout=5000,
        )
    except Exception:
        page.evaluate("""() => {
            const sel = document.querySelector('select[data-range-id="semantic-domain-ddp4"]');
            if (sel && window.rangesLoader) {
                window.rangesLoader.populateSelect(sel, 'semantic-domain-ddp4', { emptyOption: 'Select semantic domain(s)' });
            }
        }""")
        page.wait_for_timeout(500)

    # Try selecting and verify selection count; retry a few times if necessary
    deadline = time.time() + 5.0
    last = None
    while time.time() < deadline:
        page.evaluate("""(n) => {
            const selects = document.querySelectorAll('select[data-range-id="semantic-domain-ddp4"]');
            if (selects.length === 0) return;
            const sel = selects[0];
            for (let i = 0; i < sel.options.length; i++) sel.options[i].selected = false;
            let selected = 0;
            for (let i = 1; i < sel.options.length && selected < n; i++) {
                if (sel.options[i].value) {
                    sel.options[i].selected = true;
                    selected++;
                }
            }
            sel.dispatchEvent(new Event('change', { bubbles: true }));
            sel.dispatchEvent(new Event('input', { bubbles: true }));
        }""", n)
        page.wait_for_timeout(200)
        after = page.evaluate("""() => {
            const sel = document.querySelector('select[data-range-id="semantic-domain-ddp4"]');
            const res = {selected: []};
            if (sel) {
                for (let i = 0; i < sel.options.length; i++) {
                    if (sel.options[i].selected) res.selected.push(sel.options[i].value);
                }
            }
            return res;
        }""")
        print(f"DEBUG: After first-n selection: {after}")
        if len(after.get('selected', [])) >= n:
            last = after
            break
        # Try to force populate again in case options were not available before
        page.evaluate("""() => {
            const sel = document.querySelector('select[data-range-id="semantic-domain-ddp4"]');
            if (sel && window.rangesLoader) {
                window.rangesLoader.populateSelect(sel, 'semantic-domain-ddp4', { emptyOption: 'Select semantic domain(s)' });
            }
        }""")
        page.wait_for_timeout(200)
    if last is None:
        # Final fetch for debugging
        after = page.evaluate("""() => {
            const sel = document.querySelector('select[data-range-id="semantic-domain-ddp4"]');
            const res = {selected: []};
            if (sel) {
                for (let i = 0; i < sel.options.length; i++) {
                    if (sel.options[i].selected) res.selected.push(sel.options[i].value);
                }
            }
            return res;
        }""")
        print(f"DEBUG: After first-n final selection (timeout): {after}")


@pytest.mark.integration
@pytest.mark.playwright
def test_select_single_semantic_domain(page: Page, app_url: str) -> None:
    """Test selecting a single semantic domain."""

    """Test selecting a single semantic domain."""
    base_url = app_url
    timestamp = str(int(time.time() * 1000))
    headword = f"semantic-single-{timestamp}"

    page.goto(f"{base_url}/entries/add")
    page.wait_for_selector('#entry-form', timeout=10000)

    page.fill('input.lexical-unit-text', headword)

    if page.locator('textarea[name*="definition"]:visible').count() == 0:
        page.click('#add-first-sense-btn')
        for _ in range(50):
            if page.locator('textarea[name*="definition"]:visible').count() > 0:
                break
            page.wait_for_timeout(100)

    page.locator('textarea[name*="definition"]:visible').first.fill(f"Definition for {headword}")

    # Select semantic domain using Select2
    select_semantic_domain(page, index=1)

    page.click('#save-btn', timeout=10000)
    page.wait_for_load_state('networkidle', timeout=15000)

    # Get entry ID
    entry_id = None
    for _ in range(20):
        search = search_entry(base_url, headword)
        if search.get('entries') and len(search['entries']) > 0:
            entry_id = search['entries'][0]['id']
            break
        time.sleep(0.5)
    assert entry_id, f"Could not find created entry {headword}"

    # Verify via API
    entry = get_entry(base_url, entry_id)
    senses = entry.get('senses', [])
    assert len(senses) >= 1, "Expected at least 1 sense"

    # Handle case where semantic_domains key might not exist or be None
    semantic_domains = senses[0].get('semantic_domains') or []
    assert len(semantic_domains) > 0, f"Semantic domain not found: {senses[0]}"


@pytest.mark.integration
@pytest.mark.playwright
def test_select_multiple_semantic_domains(page: Page, app_url: str) -> None:
    """Test selecting multiple semantic domains."""
    base_url = app_url
    timestamp = str(int(time.time() * 1000))
    headword = f"semantic-multi-{timestamp}"

    page.goto(f"{base_url}/entries/add")
    page.wait_for_selector('#entry-form', timeout=10000)

    page.fill('input.lexical-unit-text', headword)

    if page.locator('textarea[name*="definition"]:visible').count() == 0:
        page.click('#add-first-sense-btn')
        for _ in range(50):
            if page.locator('textarea[name*="definition"]:visible').count() > 0:
                break
            page.wait_for_timeout(100)

    page.locator('textarea[name*="definition"]:visible').first.fill(f"Definition for {headword}")

    # Select multiple domains (pick first available 2)
    select_first_n_semantic_domains(page, 2)

    page.click('#save-btn', timeout=10000)
    page.wait_for_load_state('networkidle', timeout=15000)

    # Get entry ID
    entry_id = None
    for _ in range(20):
        search = search_entry(base_url, headword)
        if search.get('entries') and len(search['entries']) > 0:
            entry_id = search['entries'][0]['id']
            break
        time.sleep(0.5)
    assert entry_id, f"Could not find created entry {headword}"

    # Verify via API
    entry = get_entry(base_url, entry_id)
    senses = entry.get('senses', [])
    assert len(senses) >= 1, "Expected at least 1 sense"
    semantic_domains = senses[0].get('semantic_domains') or []
    assert len(semantic_domains) >= 2, f"Expected at least 2 semantic domains, got: {semantic_domains}"


@pytest.mark.integration
@pytest.mark.playwright
def test_semantic_domain_persists_via_api(page: Page, app_url: str) -> None:
    """Test that semantic domains persist correctly via API."""
    base_url = app_url
    timestamp = str(int(time.time() * 1000))
    headword = f"semantic-persist-{timestamp}"

    # Create via UI
    page.goto(f"{base_url}/entries/add")
    page.wait_for_selector('#entry-form', timeout=10000)

    page.fill('input.lexical-unit-text', headword)

    if page.locator('textarea[name*="definition"]:visible').count() == 0:
        page.click('#add-first-sense-btn')
        for _ in range(50):
            if page.locator('textarea[name*="definition"]:visible').count() > 0:
                break
            page.wait_for_timeout(100)

    page.locator('textarea[name*="definition"]:visible').first.fill(f"Definition for {headword}")

    # Select a domain
    select_semantic_domain(page, index=1)

    page.click('#save-btn', timeout=10000)
    page.wait_for_load_state('networkidle', timeout=15000)

    # Get entry ID and verify via API
    entry_id = None
    for _ in range(20):
        search = search_entry(base_url, headword)
        if search.get('entries') and len(search['entries']) > 0:
            entry_id = search['entries'][0]['id']
            break
        time.sleep(0.5)
    assert entry_id, "Could not find created entry"

    entry = get_entry(base_url, entry_id)
    senses = entry.get('senses', [])
    semantic_domains = senses[0].get('semantic_domains') or []
    assert len(semantic_domains) > 0, f"Semantic domain not persisted: {semantic_domains}"


@pytest.mark.integration
@pytest.mark.playwright
def test_semantic_domain_displays_in_view(page: Page, app_url: str) -> None:
    """Test that semantic domains display correctly in view page."""
    base_url = app_url
    timestamp = str(int(time.time() * 1000))
    headword = f"semantic-display-{timestamp}"

    page.goto(f"{base_url}/entries/add")
    page.wait_for_selector('#entry-form', timeout=10000)

    page.fill('input.lexical-unit-text', headword)

    if page.locator('textarea[name*="definition"]:visible').count() == 0:
        page.click('#add-first-sense-btn')
        for _ in range(50):
            if page.locator('textarea[name*="definition"]:visible').count() > 0:
                break
            page.wait_for_timeout(100)

    page.locator('textarea[name*="definition"]:visible').first.fill(f"Definition for {headword}")

    # Select a domain
    select_semantic_domain(page, index=1)

    page.click('#save-btn', timeout=10000)
    page.wait_for_load_state('networkidle', timeout=15000)

    # Get entry and domain text
    entry_id = None
    for _ in range(20):
        search = search_entry(base_url, headword)
        if search.get('entries') and len(search['entries']) > 0:
            entry_id = search['entries'][0]['id']
            break
        time.sleep(0.5)
    assert entry_id, "Could not find created entry"

    entry = get_entry(base_url, entry_id)
    domain_values = (entry.get('senses', [])[0].get('semantic_domains') or [])
    assert domain_values, "No semantic domain found via API"
    domain_text = domain_values[0]

    # Visit view page and assert domain text appears somewhere in the rendered page (display profile may hide badges)
    page.goto(f"{base_url}/entries/{entry_id}", timeout=15000)
    try:
        page.wait_for_selector('.sense-item', timeout=10000)
    except Exception:
        # Fallback to ensure page finished loading
        page.wait_for_load_state('networkidle', timeout=15000)

    body_text = page.locator('body').inner_text()
    assert domain_text in body_text, f"Domain text '{domain_text}' not found in view page"






@pytest.mark.integration
@pytest.mark.playwright
def test_deselect_all_semantic_domains(page: Page, app_url: str) -> None:
    """Test removing all semantic domain selections."""
    base_url = app_url
    timestamp = str(int(time.time() * 1000))
    headword = f"semantic-deselect-{timestamp}"

    # Create entry with domain first
    page.goto(f"{base_url}/entries/add")
    page.wait_for_selector('#entry-form', timeout=10000)

    page.fill('input.lexical-unit-text', headword)

    if page.locator('textarea[name*="definition"]:visible').count() == 0:
        page.click('#add-first-sense-btn')
        for _ in range(50):
            if page.locator('textarea[name*="definition"]:visible').count() > 0:
                break
            page.wait_for_timeout(100)

    page.locator('textarea[name*="definition"]:visible').first.fill(f"Definition for {headword}")

    # Select a domain
    select_semantic_domain(page, index=1)

    page.click('#save-btn', timeout=10000)
    page.wait_for_load_state('networkidle', timeout=15000)

    # Get entry ID
    entry_id = None
    for _ in range(20):
        search = search_entry(base_url, headword)
        if search.get('entries') and len(search['entries']) > 0:
            entry_id = search['entries'][0]['id']
            break
        time.sleep(0.5)
    assert entry_id, "Could not find created entry"

    # Edit and deselect domain
    page.goto(f"{base_url}/entries/{entry_id}/edit")
    page.wait_for_selector('#entry-form', timeout=10000)

    # Deselect - clear the select
    semantic_select = page.locator('select[data-range-id="semantic-domain-ddp4"]').first
    if semantic_select.count() > 0:
        semantic_select.select_option(index=0)  # Select placeholder

    # The live-preview module has a 500 ms debounce.  If the browser is already in
    # networkidle state before the debounce fires, wait_for_load_state("networkidle")
    # returns immediately and save is clicked while the debounce-triggered live-preview
    # POST is still arriving — blocking the FormSerializer WebWorker GET on the
    # single-threaded Flask server.  Waiting >500 ms here guarantees the debounce fires
    # first and the subsequent networkidle call drains that POST before we click save.
    page.wait_for_timeout(800)
    try:
        page.wait_for_load_state('networkidle', timeout=10000)
    except Exception:
        pass  # Proceed even if networkidle times out; the 800 ms wait above already
              # guaranteed the debounce-triggered live-preview POST was dispatched.

    # Use expect_response to wait for the actual PUT to complete.
    # wait_for_load_state('networkidle') alone fires prematurely because submitForm()
    # uses async WebWorker serialization – no HTTP request is active during that phase.
    with page.expect_response(
        lambda r: f"/api/xml/entries/{entry_id}" in r.url and r.request.method == "PUT",
        timeout=20000,
    ):
        # Calling submitForm() directly is more reliable in tests than a native click
        # because the save button is at the bottom of the form and may be below
        # the default Playwright viewport, causing native clicks to miss it.
        page.evaluate("() => submitForm()")

    # Verify domains removed via API
    entry = get_entry(base_url, entry_id)
    senses = entry.get('senses', [])
    semantic_domains = senses[0].get('semantic_domains') or []

    assert len(semantic_domains) == 0, f"Semantic domain should be removed: {semantic_domains}"


@pytest.mark.integration
@pytest.mark.playwright
def test_semantic_domain_roundtrip(page: Page, app_url: str) -> None:
    """Comprehensive round-trip test for semantic domains."""
    base_url = app_url
    timestamp = str(int(time.time() * 1000))
    headword = f"semantic-roundtrip-{timestamp}"

    # Create via UI with two domains
    page.goto(f"{base_url}/entries/add")
    page.wait_for_selector('#entry-form', timeout=10000)

    page.fill('input.lexical-unit-text', headword)

    if page.locator('textarea[name*="definition"]:visible').count() == 0:
        page.click('#add-first-sense-btn')
        for _ in range(50):
            if page.locator('textarea[name*="definition"]:visible').count() > 0:
                break
            page.wait_for_timeout(100)

    page.locator('textarea[name*="definition"]:visible').first.fill(f"Definition for {headword}")

    select_first_n_semantic_domains(page, 2)

    page.click('#save-btn', timeout=10000)
    page.wait_for_load_state('networkidle', timeout=15000)

    # Verify saved
    entry_id = None
    for _ in range(20):
        search = search_entry(base_url, headword)
        if search.get('entries') and len(search['entries']) > 0:
            entry_id = search['entries'][0]['id']
            break
        time.sleep(0.5)
    assert entry_id, "Could not find created entry"

    entry = get_entry(base_url, entry_id)
    semantic_domains = entry.get('senses', [])[0].get('semantic_domains') or []
    assert len(semantic_domains) >= 2, f"Expected multiple semantic domains saved, got: {semantic_domains}"

    # Edit and remove one domain (keep only first)
    page.goto(f"{base_url}/entries/{entry_id}/edit")
    page.wait_for_selector('#entry-form', timeout=10000)

    # Select only the first domain by index
    select_multiple_semantic_domains(page, [1])

    # The live-preview module has a 500 ms debounce.  The helper above already waits
    # 200 ms internally; we wait an additional 800 ms (>500 ms) so the debounce fires
    # and the resulting POST is visible before networkidle is checked.  Without this
    # the browser can be in networkidle state before the debounce fires, causing
    # wait_for_load_state to return too early and the live-preview POST to race with
    # the FormSerializer WebWorker GET on the single-threaded Flask server.
    page.wait_for_timeout(800)
    try:
        page.wait_for_load_state('networkidle', timeout=10000)
    except Exception:
        pass  # Proceed even if networkidle times out; the 800 ms wait above already
              # guaranteed the debounce-triggered live-preview POST was dispatched.

    # Use expect_response to wait for the actual PUT to complete.
    # wait_for_load_state('networkidle') alone fires prematurely because submitForm()
    # uses async WebWorker serialization – no HTTP request is active during that phase.
    with page.expect_response(
        lambda r: f"/api/xml/entries/{entry_id}" in r.url and r.request.method == "PUT",
        timeout=20000,
    ):
        # Calling submitForm() directly is more reliable in tests than a native click
        # because the save button is at the bottom of the form and may be below
        # the default Playwright viewport, causing native clicks to miss it.
        page.evaluate("() => submitForm()")

    entry = get_entry(base_url, entry_id)
    semantic_domains = entry.get('senses', [])[0].get('semantic_domains') or []
    assert len(semantic_domains) == 1, f"Expected one semantic domain after edit, got: {semantic_domains}"
