"""§16.3 B0 gate: entry-level custom fields must round-trip through the Alpine path.

Before the port, `serializeEntry` never emitted custom_fields and the server does
delete+insert of the posted XML, so any edit-save silently dropped them. This test
proves they now persist (and render + edit) via the `entryCustomFields` component.
"""
import time
import uuid
import pytest
import requests
from playwright.sync_api import Page


@pytest.mark.integration
@pytest.mark.playwright
def test_custom_field_roundtrips(page: Page, app_url: str) -> None:
    eid = f"cf_{uuid.uuid4().hex[:8]}"
    lift_xml = (
        f'<entry xmlns="http://fieldworks.sil.org/schemas/lift/0.13" id="{eid}">'
        '<lexical-unit><form lang="en"><text>cfhead</text></form></lexical-unit>'
        '<sense id="s1"><definition><form lang="en"><text>d</text></form></definition></sense>'
        '<field type="usage_note"><form lang="en"><text>ORIGINAL_NOTE</text></form></field>'
        '</entry>'
    )
    r = requests.post(
        f"{app_url}/api/xml/entries",
        data=lift_xml.encode("utf-8"),
        headers={"Content-Type": "application/xml"},
    )
    assert r.status_code in (200, 201), f"create failed: {r.status_code} {r.text[:200]}"

    page.goto(f"{app_url}/entries/{eid}/edit")
    page.wait_for_selector("#entry-form", timeout=10000)
    # Custom-fields section is x-show'd once Alpine reads the field; the textarea is
    # x-model="fields[ft][lang]" — confirm normalizeEntry populated it.
    ta = page.locator(".custom-fields-section textarea").first
    ta.wait_for(state="visible", timeout=10000)
    assert ta.input_value() == "ORIGINAL_NOTE", "custom field did not populate on edit-load"

    # Edit it and save.
    ta.fill("EDITED_NOTE")
    page.wait_for_timeout(150)
    with page.expect_response(
        lambda resp: "/api/xml/entries" in resp.url and resp.request.method in ("POST", "PUT"),
        timeout=20000,
    ):
        page.evaluate("() => submitForm()")

    # Reload the stored XML and assert the edited custom field persisted.
    xml = ""
    for _ in range(20):
        xml = requests.get(f"{app_url}/api/xml/entries/{eid}").text
        if "EDITED_NOTE" in xml:
            break
        time.sleep(0.4)
    assert 'type="usage_note"' in xml and "EDITED_NOTE" in xml, \
        "custom field not persisted via Alpine path (regressed/dropped): " + xml[:400]
