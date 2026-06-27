"""Round-trip test for entry-level annotations (spec §16.2)."""
import time
import pytest
import requests
from playwright.sync_api import Page


@pytest.mark.integration
@pytest.mark.playwright
def test_entry_annotation_roundtrip(page: Page, app_url: str) -> None:
    hw = f"ann-{int(time.time()*1000)}"
    page.goto(f"{app_url}/entries/add")
    page.wait_for_selector('#entry-form', timeout=10000)
    page.fill('input.lexical-unit-text', hw)
    page.locator('textarea.definition-text:visible').first.fill("def")

    page.locator('.add-annotation-btn').first.click()
    page.wait_for_timeout(200)
    page.locator('.annotation-name-input').first.fill("editorial-status")
    page.locator('input[x-model="ann.value"]').first.fill("checked")
    page.wait_for_timeout(150)

    assert page.locator('.annotation-item').count() == 1, "duplicate annotation control"

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
    assert '<annotation' in xml and 'editorial-status' in xml and 'checked' in xml, \
        "annotation not persisted: " + xml[:300]
