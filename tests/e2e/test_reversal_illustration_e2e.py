import time, json
import pytest, requests
from playwright.sync_api import Page


@pytest.mark.integration
@pytest.mark.playwright
def test_reversal_illustration_roundtrip(page: Page, app_url: str) -> None:
    base_url = app_url
    headword = f"revill-{int(time.time()*1000)}"
    page.goto(f"{base_url}/entries/add")
    page.wait_for_selector('#entry-form', timeout=10000)
    page.fill('input.lexical-unit-text', headword)
    page.locator('textarea.definition-text:visible').first.fill("revill def")

    # Reversal: add, pick a language type, fill the form (x-model rev.forms[rev.type])
    page.locator('.add-reversal-btn').first.click()
    page.wait_for_timeout(200)
    lang = page.evaluate("""() => {
        const d = window.Alpine.$data(document.querySelector('[x-data^="senseTree"]'));
        return (d.languageOptions[0] || {}).code;
    }""")
    page.locator('.reversal-type-select').first.select_option(lang)
    page.wait_for_timeout(100)
    page.locator('.reversal-form-input').first.fill("rev-headword")

    # Illustration: add, fill href
    page.locator('.add-illustration-btn').first.click()
    page.wait_for_timeout(200)
    page.locator('.illustration-item input[type="text"]').first.fill("images/probe.jpg")
    page.wait_for_timeout(200)

    state = page.evaluate("""() => {
        const d = window.Alpine.$data(document.querySelector('[x-data^="senseTree"]'));
        const s = d.senses[0];
        return { reversals: s.reversals, illustrations: s.illustrations,
                 illCount: document.querySelectorAll('.illustration-item').length,
                 revCount: document.querySelectorAll('.reversal-item').length };
    }""")

    with page.expect_response(lambda r: "/api/xml/entries" in r.url and r.request.method in ("POST", "PUT"), timeout=20000):
        page.evaluate("() => submitForm()")

    entry_id = None
    for _ in range(20):
        s = requests.get(f"{base_url}/api/search?q={headword}&limit=10").json()
        ents = s.get('entries') or s.get('results') or []
        if ents:
            entry_id = ents[0]['id']; break
        time.sleep(0.5)
    assert entry_id, "entry not found"
    xml = requests.get(f"{base_url}/api/xml/entries/{entry_id}").text

    assert state["revCount"] == 1 and state["illCount"] == 1, state
    assert 'rev-headword' in xml, "reversal form not persisted"
    assert 'images/probe.jpg' in xml, "illustration href not persisted"
