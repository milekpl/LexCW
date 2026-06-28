"""Round-trip: a sense-level annotation entered via the Alpine UI must reach the saved LIFT XML
(spec gap restore). The model layer was already tested; this proves UI -> state -> adapter ->
serializer -> save end to end."""
import time
import pytest
import requests
from playwright.sync_api import Page


@pytest.mark.integration
@pytest.mark.playwright
def test_sense_annotation_roundtrip(page: Page, app_url: str) -> None:
    hw = f"sann-{int(time.time()*1000)}"
    page.goto(f"{app_url}/entries/add")
    page.wait_for_selector('#entry-form', timeout=10000)
    page.fill('input.lexical-unit-text', hw)
    page.locator('textarea.definition-text:visible').first.fill("def")

    sense = page.locator('.sense-item').first
    sense.locator('.add-annotation-btn').first.click()
    page.wait_for_timeout(300)
    ann = sense.locator('.annotation-item').first
    ann.locator('.annotation-name-input').first.fill("flagged")
    ann.locator('input[x-model="ann.value"]').first.fill("needs-review")
    page.wait_for_timeout(200)

    assert sense.locator('.annotation-item').count() == 1, "duplicate sense annotation control"

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
    # the annotation must be INSIDE the <sense>, with name+value
    assert '<sense' in xml and 'flagged' in xml and 'needs-review' in xml, \
        "sense annotation not persisted: " + xml[:400]
