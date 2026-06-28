"""Citation/status must persist on save (data-loss fix: serializeEntry now emits them)."""
import time
import pytest
import requests
from playwright.sync_api import Page


@pytest.mark.integration
@pytest.mark.playwright
def test_citation_persists(page: Page, app_url: str) -> None:
    hw = f"cit-{int(time.time()*1000)}"
    page.goto(f"{app_url}/entries/add")
    page.wait_for_selector('#entry-form', timeout=10000)
    page.fill('input.lexical-unit-text', hw)
    page.locator('textarea.definition-text:visible').first.fill("def")
    page.fill('#citation-form', "cited-form-xyz")
    page.wait_for_timeout(150)

    with page.expect_response(
        lambda r: "/api/xml/entries" in r.url and r.request.method in ("POST", "PUT"),
        timeout=20000,
    ):
        page.evaluate("() => submitForm()")

    eid = None
    for _ in range(20):
        ents = requests.get(f"{app_url}/api/search?q={hw}&limit=10").json().get('entries') or []
        if ents:
            eid = ents[0]['id']; break
        time.sleep(0.5)
    assert eid, "entry not found"
    xml = requests.get(f"{app_url}/api/xml/entries/{eid}").text
    assert '<citation' in xml and 'cited-form-xyz' in xml, \
        "citation not persisted (still dropped): " + xml[:400]


@pytest.mark.integration
@pytest.mark.playwright
def test_citation_repopulates_on_edit(page: Page, app_url: str) -> None:
    """Round-trip the other direction: a saved citation must repopulate the
    Alpine-bound #citation-form input on edit-load (normalizeEntry path)."""
    hw = f"citedit-{int(time.time()*1000)}"
    page.goto(f"{app_url}/entries/add")
    page.wait_for_selector('#entry-form', timeout=10000)
    page.fill('input.lexical-unit-text', hw)
    page.locator('textarea.definition-text:visible').first.fill("def")
    page.fill('#citation-form', "round-trip-cit")
    page.wait_for_timeout(150)
    with page.expect_response(
        lambda r: "/api/xml/entries" in r.url and r.request.method in ("POST", "PUT"),
        timeout=20000,
    ):
        page.evaluate("() => submitForm()")

    eid = None
    for _ in range(20):
        ents = requests.get(f"{app_url}/api/search?q={hw}&limit=10").json().get('entries') or []
        if ents:
            eid = ents[0]['id']; break
        time.sleep(0.5)
    assert eid, "entry not found"

    page.goto(f"{app_url}/entries/{eid}/edit")
    page.wait_for_selector('#entry-form', timeout=10000)
    page.wait_for_timeout(300)  # let Alpine init + normalizeEntry populate
    value = page.input_value('#citation-form')
    assert value == "round-trip-cit", f"citation did not repopulate on edit: {value!r}"


@pytest.mark.integration
@pytest.mark.playwright
def test_status_persists(page: Page, app_url: str) -> None:
    """Status is now Alpine-owned (entryMeta.status). Set it via the reactive
    state (the test DB may have no 'status' range, so the dropdown can be empty)
    and confirm it persists as an entry-level <trait name="status">."""
    hw = f"stat-{int(time.time()*1000)}"
    page.goto(f"{app_url}/entries/add")
    page.wait_for_selector('#entry-form', timeout=10000)
    page.fill('input.lexical-unit-text', hw)
    page.locator('textarea.definition-text:visible').first.fill("def")
    # Drive the Alpine-owned status through reactive state (range-independent).
    page.evaluate(
        "() => { const el = document.querySelector('[x-data^=\"entryMeta\"]');"
        " window.Alpine.$data(el).status = 'draft'; }"
    )
    page.wait_for_timeout(150)

    with page.expect_response(
        lambda r: "/api/xml/entries" in r.url and r.request.method in ("POST", "PUT"),
        timeout=20000,
    ):
        page.evaluate("() => submitForm()")

    eid = None
    for _ in range(20):
        ents = requests.get(f"{app_url}/api/search?q={hw}&limit=10").json().get('entries') or []
        if ents:
            eid = ents[0]['id']; break
        time.sleep(0.5)
    assert eid, "entry not found"
    xml = requests.get(f"{app_url}/api/xml/entries/{eid}").text
    assert '<trait name="status" value="draft"' in xml, \
        "status not persisted via Alpine path: " + xml[:400]
