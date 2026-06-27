"""Round-trip test for entry-level variant relations (outgoing) (spec §16.2.3).

Adds a variant relation via the real Alpine UI, submits, reloads the saved
entry via the API, and asserts the relation persisted into the saved LIFT XML.
The serializer converts variant_relations into <relation> elements carrying a
<trait name="variant-type" .../> child.
"""
import time
import pytest
import requests
from playwright.sync_api import Page


@pytest.mark.integration
@pytest.mark.playwright
def test_variant_relation_roundtrip(page: Page, app_url: str) -> None:
    hw = f"var-rel-{int(time.time()*1000)}"
    page.goto(f"{app_url}/entries/add")
    page.wait_for_selector('#entry-form', timeout=10000)
    page.fill('input.lexical-unit-text', hw)
    page.locator('textarea.definition-text:visible').first.fill("def")

    # Add an outgoing variant relation via the Alpine UI.
    page.locator('.add-variant-btn').first.click()
    page.wait_for_selector('.variants-section select.dynamic-lift-range', timeout=10000)

    # Read a real variant-type option value from the Alpine component state.
    val = page.evaluate(
        '''() => {
            const root = document.querySelector('[x-data^="entryVariantRelations"]');
            if (!root || !window.Alpine) return "";
            const d = window.Alpine.$data(root);
            const o = (d && d.variantTypeOptions) || [];
            return o.length ? o[0].value : "";
        }'''
    )
    assert val, "no variant-type options loaded from range data"

    page.locator('.variants-section select.dynamic-lift-range').first.select_option(val)
    page.locator('.variants-section input[type="text"]').first.fill("variant-target-id")
    page.wait_for_timeout(150)

    # Exactly one variant control rendered (no duplicate).
    assert page.locator('.variants-section .variant-item[data-direction="outgoing"]').count() == 1, \
        "duplicate variant control"

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
        if 'relation' in line or 'variant-type' in line or 'variant-target-id' in line:
            print("XML:", line.strip())

    assert '<relation' in xml, "no <relation> element persisted: " + xml[:400]
    assert 'variant-target-id' in xml, "variant ref not persisted: " + xml[:400]
    assert 'variant-type' in xml, "variant-type trait not persisted: " + xml[:400]
    # The chosen range value should appear as the trait value.
    assert val in xml, f"variant-type value '{val}' not persisted: " + xml[:400]
