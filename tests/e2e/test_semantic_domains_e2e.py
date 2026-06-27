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


def _wait_semantic_options(page: Page, minimum: int = 1) -> None:
    """Wait until the Alpine senseTree has loaded at least `minimum` semantic-domain options."""
    page.wait_for_function(
        """(min) => {
            const el = document.querySelector('[x-data^="senseTree"]');
            if (!el || !window.Alpine) return false;
            const d = window.Alpine.$data(el);
            const rd = d.rangeData && d.rangeData['semantic-domain-ddp4'];
            return Array.isArray(rd) && rd.length >= min;
        }""",
        arg=minimum,
        timeout=8000,
    )


def _semantic_option_values(page: Page, indices: list[int]) -> list[str]:
    """Resolve a list of rangeData indices to their option values."""
    return page.evaluate("""(indices) => {
        const d = window.Alpine.$data(document.querySelector('[x-data^="senseTree"]'));
        const opts = d.rangeData['semantic-domain-ddp4'] || [];
        const out = [];
        for (const idx of indices) {
            if (idx >= 0 && idx < opts.length && opts[idx].value) out.push(opts[idx].value);
        }
        return out;
    }""", indices)


def select_semantic_domain(page: Page, index: int = 1) -> None:
    """Select a semantic domain through the REAL <select x-model> (drives the UI binding)."""
    _wait_semantic_options(page, index + 1)
    values = _semantic_option_values(page, [index])
    assert values, f"No semantic-domain option at index {index}"
    page.locator('select.sense-semantic-domain-select').first.select_option(values)
    page.wait_for_timeout(100)
    print(f"DEBUG: Selected semantic domain: {values}")


def select_multiple_semantic_domains(page: Page, indices: list[int]) -> None:
    """Select multiple semantic domains through the REAL <select multiple x-model>."""
    _wait_semantic_options(page, (max(indices) + 1) if indices else 1)
    values = _semantic_option_values(page, indices)
    if not values:
        values = _semantic_option_values(page, [0])
    page.locator('select.sense-semantic-domain-select').first.select_option(values)
    page.wait_for_timeout(100)
    print(f"DEBUG: Selected semantic domains: {values}")


def select_first_n_semantic_domains(page: Page, n: int = 2) -> None:
    """Select the first n semantic domains through the REAL <select multiple x-model>."""
    try:
        _wait_semantic_options(page, n)
    except Exception:
        pass  # proceed with whatever loaded
    values = _semantic_option_values(page, list(range(n)))
    assert values, "No semantic-domain options loaded"
    page.locator('select.sense-semantic-domain-select').first.select_option(values)
    page.wait_for_timeout(100)
    print(f"DEBUG: Selected first-{n} semantic domains: {values}")



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

    if page.locator('textarea.definition-text:visible').count() == 0:
        page.click('#add-first-sense-btn')
        for _ in range(50):
            if page.locator('textarea.definition-text:visible').count() > 0:
                break
            page.wait_for_timeout(100)

    page.locator('textarea.definition-text:visible').first.fill(f"Definition for {headword}")

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

    if page.locator('textarea.definition-text:visible').count() == 0:
        page.click('#add-first-sense-btn')
        for _ in range(50):
            if page.locator('textarea.definition-text:visible').count() > 0:
                break
            page.wait_for_timeout(100)

    page.locator('textarea.definition-text:visible').first.fill(f"Definition for {headword}")

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

    if page.locator('textarea.definition-text:visible').count() == 0:
        page.click('#add-first-sense-btn')
        for _ in range(50):
            if page.locator('textarea.definition-text:visible').count() > 0:
                break
            page.wait_for_timeout(100)

    page.locator('textarea.definition-text:visible').first.fill(f"Definition for {headword}")

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

    if page.locator('textarea.definition-text:visible').count() == 0:
        page.click('#add-first-sense-btn')
        for _ in range(50):
            if page.locator('textarea.definition-text:visible').count() > 0:
                break
            page.wait_for_timeout(100)

    page.locator('textarea.definition-text:visible').first.fill(f"Definition for {headword}")

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

    if page.locator('textarea.definition-text:visible').count() == 0:
        page.click('#add-first-sense-btn')
        for _ in range(50):
            if page.locator('textarea.definition-text:visible').count() > 0:
                break
            page.wait_for_timeout(100)

    page.locator('textarea.definition-text:visible').first.fill(f"Definition for {headword}")

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
    semantic_select = page.locator('.sense-semantic-domain-select').first
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

    if page.locator('textarea.definition-text:visible').count() == 0:
        page.click('#add-first-sense-btn')
        for _ in range(50):
            if page.locator('textarea.definition-text:visible').count() > 0:
                break
            page.wait_for_timeout(100)

    page.locator('textarea.definition-text:visible').first.fill(f"Definition for {headword}")

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
