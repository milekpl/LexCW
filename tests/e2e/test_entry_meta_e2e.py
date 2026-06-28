"""Round-trip persistence tests for entry-level POS (grammatical_info) and morph_type
(Part A of the plan: port entry-level scalar fields to Alpine entryMeta component).

Gates (plan §5):
  - POS:       set entry POS via Alpine UI → submitForm() → reload XML →
               assert <grammatical-info value="…"> at ENTRY level (before the first <sense>).
  - morph_type: same path → assert <trait name="morph-type" value="…"> at entry level.
  - No regressions: POS propagation to senses still works (tested by test_pos_ui.py).

IMPORTANT: These tests prove UI→state→adapter→serializer→save. They do NOT verify that
           citation/status round-trip (that's the Part B diagnostic).
"""
import time
import pytest
import requests
from playwright.sync_api import Page


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _wait_for_entry_meta(page: Page, timeout_ms: int = 10000) -> None:
    """Wait until the entryMeta Alpine component is initialised on the page."""
    page.wait_for_function(
        """() => {
            const el = document.querySelector('[x-data^="entryMeta"]');
            return !!(el && window.Alpine && window.Alpine.$data(el));
        }""",
        timeout=timeout_ms,
    )


def _set_entry_meta(page: Page, grammatical_info: str = '', morph_type: str = '') -> None:
    """Set entry-meta state directly via Alpine.$data — bypasses range loading."""
    page.evaluate(
        """([gi, mt]) => {
            const el = document.querySelector('[x-data^="entryMeta"]');
            if (!el || !window.Alpine) throw new Error('entryMeta component not found');
            const d = window.Alpine.$data(el);
            if (gi !== '') d.grammaticalInfo = gi;
            if (mt !== '') d.morphType = mt;
        }""",
        [grammatical_info, morph_type],
    )


def _save_and_get_xml(page: Page, app_url: str, headword: str) -> str:
    """Submit the form, poll for the new entry, and return its XML."""
    with page.expect_response(
        lambda r: "/api/xml/entries" in r.url and r.request.method in ("POST", "PUT"),
        timeout=20000,
    ):
        page.evaluate("() => submitForm()")

    eid = None
    for _ in range(30):
        resp = requests.get(f"{app_url}/api/search?q={headword}&limit=10")
        ents = resp.json().get("entries") or []
        if ents:
            eid = ents[0]["id"]
            break
        time.sleep(0.5)
    assert eid, f"Entry '{headword}' not found after save"
    xml = requests.get(f"{app_url}/api/xml/entries/{eid}").text
    return xml


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

@pytest.mark.integration
@pytest.mark.playwright
def test_entry_pos_roundtrip(page: Page, app_url: str) -> None:
    """POS set via Alpine entryMeta → saved → reloaded → <grammatical-info> at ENTRY level.

    The entry-level grammatical-info must appear BEFORE the first <sense> element in the
    serialized XML (proving it is entry-level, not injected into a sense by mistake).
    """
    hw = f"emeta-pos-{int(time.time() * 1000)}"

    page.goto(f"{app_url}/entries/add")
    page.wait_for_selector("#entry-form", timeout=10000)
    page.fill("input.lexical-unit-text", hw)
    # Add a definition so the form passes validation
    page.locator("textarea.definition-text:visible").first.fill("test definition for POS round-trip")

    _wait_for_entry_meta(page)
    _set_entry_meta(page, grammatical_info="Noun")

    # Confirm the select reflects the value (Alpine x-model is live)
    value_in_select = page.evaluate(
        "() => document.getElementById('part-of-speech').value"
    )
    assert value_in_select == "Noun", f"Entry POS select not updated: got '{value_in_select}'"

    xml = _save_and_get_xml(page, app_url, hw)

    # Structural assertion: entry-level grammatical-info must appear before first <sense>
    gram_pos = xml.find('<grammatical-info value="Noun"')
    sense_pos = xml.find("<sense ")
    assert gram_pos != -1, (
        f"<grammatical-info value=\"Noun\"> not found in saved XML.\nXML: {xml[:600]}"
    )
    assert sense_pos != -1, "No <sense> found in saved XML — unexpected."
    assert gram_pos < sense_pos, (
        "Entry-level <grammatical-info> appears AFTER <sense> — it's at sense level, not entry level.\n"
        f"grammatical-info at pos {gram_pos}, sense at pos {sense_pos}.\nXML: {xml[:600]}"
    )


@pytest.mark.integration
@pytest.mark.playwright
def test_entry_morph_type_roundtrip(page: Page, app_url: str) -> None:
    """morph_type set via Alpine entryMeta → saved → reloaded → <trait name="morph-type"> present.

    The trait must appear before the first <sense> element (entry level, not sense level).
    """
    hw = f"emeta-mt-{int(time.time() * 1000)}"

    page.goto(f"{app_url}/entries/add")
    page.wait_for_selector("#entry-form", timeout=10000)
    page.fill("input.lexical-unit-text", hw)
    page.locator("textarea.definition-text:visible").first.fill("test definition for morph-type round-trip")

    _wait_for_entry_meta(page)
    _set_entry_meta(page, morph_type="stem")

    xml = _save_and_get_xml(page, app_url, hw)

    morph_pos = xml.find('<trait name="morph-type" value="stem"')
    sense_pos = xml.find("<sense ")
    assert morph_pos != -1, (
        f"<trait name=\"morph-type\" value=\"stem\"> not found in saved XML.\nXML: {xml[:600]}"
    )
    assert sense_pos != -1, "No <sense> found in saved XML — unexpected."
    assert morph_pos < sense_pos, (
        "morph-type <trait> appears AFTER <sense> — it's at sense level, not entry level.\n"
        f"morph-type at pos {morph_pos}, sense at pos {sense_pos}.\nXML: {xml[:600]}"
    )


@pytest.mark.integration
@pytest.mark.playwright
def test_entry_pos_and_morph_type_together(page: Page, app_url: str) -> None:
    """Both POS and morph_type set together round-trip correctly."""
    hw = f"emeta-both-{int(time.time() * 1000)}"

    page.goto(f"{app_url}/entries/add")
    page.wait_for_selector("#entry-form", timeout=10000)
    page.fill("input.lexical-unit-text", hw)
    page.locator("textarea.definition-text:visible").first.fill("test definition for combined round-trip")

    _wait_for_entry_meta(page)
    _set_entry_meta(page, grammatical_info="Verb", morph_type="stem")

    xml = _save_and_get_xml(page, app_url, hw)

    assert '<grammatical-info value="Verb"' in xml, (
        f"POS Verb not found.\nXML: {xml[:600]}"
    )
    assert '<trait name="morph-type" value="stem"' in xml, (
        f"morph-type stem not found.\nXML: {xml[:600]}"
    )
    # Both must be at entry level (before first <sense>)
    sense_pos = xml.find("<sense ")
    gram_pos = xml.find('<grammatical-info value="Verb"')
    morph_pos = xml.find('<trait name="morph-type" value="stem"')
    assert gram_pos < sense_pos, "POS not at entry level"
    assert morph_pos < sense_pos, "morph-type not at entry level"


@pytest.mark.integration
@pytest.mark.playwright
def test_citation_status_diagnostic(page: Page, app_url: str) -> None:
    """Part B Step 1: diagnostic — do citation_form and status currently round-trip?

    This test sets citation + status via the CURRENT legacy inputs (name= selects/inputs),
    saves, and checks whether those fields appear in the saved XML.

    The result determines whether a serializer gap exists. Per plan §3:
      - If they DO appear → trace the path (server-side?), then port to Alpine.
      - If they do NOT appear → pre-existing serializer gap; do NOT port without fixing.

    FINDING reported in the test output. This test ALWAYS PASSES — it is diagnostic only.
    It does not assert persistence; it reports what it finds.
    """
    hw = f"emeta-diag-{int(time.time() * 1000)}"

    page.goto(f"{app_url}/entries/add")
    page.wait_for_selector("#entry-form", timeout=10000)
    page.fill("input.lexical-unit-text", hw)
    page.locator("textarea.definition-text:visible").first.fill("diagnostic definition")

    # Set citation_form via the legacy input (name= input, still present)
    citation_present = page.locator("#citation-form").count() > 0
    if citation_present:
        page.fill("#citation-form", "diagnostic-citation")

    # Set status via the legacy select (name= select, still present)
    status_present = page.locator("#status").count() > 0
    if status_present:
        # Just set a status value directly via JS; the range may not have loaded
        page.evaluate(
            """() => {
                const sel = document.getElementById('status');
                if (!sel) return;
                // Try to set a value if options exist; if no options, leave empty.
                for (const opt of sel.options) {
                    if (opt.value && opt.value !== '') {
                        sel.value = opt.value;
                        sel.dispatchEvent(new Event('change', {bubbles: true}));
                        break;
                    }
                }
            }"""
        )
        status_value_set = page.evaluate(
            "() => document.getElementById('status') ? document.getElementById('status').value : ''"
        )
    else:
        status_value_set = ""

    # Save and retrieve XML
    with page.expect_response(
        lambda r: "/api/xml/entries" in r.url and r.request.method in ("POST", "PUT"),
        timeout=20000,
    ):
        page.evaluate("() => submitForm()")

    eid = None
    for _ in range(30):
        resp = requests.get(f"{app_url}/api/search?q={hw}&limit=10")
        ents = resp.json().get("entries") or []
        if ents:
            eid = ents[0]["id"]
            break
        time.sleep(0.5)
    assert eid, f"Diagnostic entry '{hw}' not found after save"

    xml = requests.get(f"{app_url}/api/xml/entries/{eid}").text

    # Check what round-tripped
    citation_in_xml = "diagnostic-citation" in xml
    citation_element_in_xml = "<citation" in xml
    status_in_xml = '<trait name="status"' in xml or "<field type=\"status\"" in xml

    # DIAGNOSTIC FINDING — always print, always pass
    finding_lines = [
        "",
        "=== PART B CITATION/STATUS DIAGNOSTIC FINDING ===",
        f"  citation_form input present: {citation_present}",
        f"  status input present: {status_present}",
        f"  status value set to: '{status_value_set}'",
        f"  citation text ('diagnostic-citation') in XML: {citation_in_xml}",
        f"  <citation element in XML: {citation_element_in_xml}",
        f"  status trait/field in XML: {status_in_xml}",
        f"  XML excerpt: {xml[:500]}",
        "=================================================",
    ]
    print("\n".join(finding_lines))

    # Conclusion for the plan
    if citation_in_xml:
        print("FINDING: citation_form DOES round-trip → investigate existing path, then port.")
    else:
        print("FINDING: citation_form is SILENTLY DROPPED → pre-existing serializer gap (plan §3).")

    if status_in_xml:
        print("FINDING: status DOES round-trip → investigate existing path, then port.")
    else:
        if status_value_set:
            print("FINDING: status is SILENTLY DROPPED → pre-existing serializer gap (plan §3).")
        else:
            print("FINDING: status had no options to set (range not loaded in test env) → inconclusive.")

    # This test always passes — it is diagnostic only
