"""Round-trip test for entry-level direct variants / allomorphs (spec §16.2.3).

Adds a direct variant (inline <variant> with a multilingual <form>) via the
real Alpine UI, submits, reloads the saved entry via the API, and asserts the
form text persisted into the saved LIFT XML inside a <variant>/<form>/<text>.
"""
import time
import pytest
import requests
from playwright.sync_api import Page


@pytest.mark.integration
@pytest.mark.playwright
def test_direct_variant_roundtrip(page: Page, app_url: str) -> None:
    hw = f"dir-var-{int(time.time()*1000)}"
    page.goto(f"{app_url}/entries/add")
    page.wait_for_selector('#entry-form', timeout=10000)
    page.fill('input.lexical-unit-text', hw)
    page.locator('textarea.definition-text:visible').first.fill("def")

    # Add a direct variant via the Alpine UI. It is seeded with a form keyed by
    # the project source language, so a text input renders immediately.
    page.locator('.add-direct-variant-btn').first.click()
    page.wait_for_selector('.direct-variants-section .direct-variant-item', timeout=10000)

    # The first text input within the item is the variant form text.
    page.locator('.direct-variant-item input[type="text"]').first.fill("allomorph-form-xyz")
    page.wait_for_timeout(150)

    # Exactly one direct variant rendered (no duplicate).
    assert page.locator('.direct-variant-item').count() == 1, "duplicate direct variant control"

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

    # Print the relevant XML lines for visibility.
    for line in xml.splitlines():
        if 'variant' in line or 'allomorph-form-xyz' in line:
            print("XML:", line.strip())

    assert '<variant' in xml, "no <variant> element persisted: " + xml[:400]
    assert 'allomorph-form-xyz' in xml, "variant form text not persisted: " + xml[:400]
