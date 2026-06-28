"""XML preview must serialize Alpine-owned state (lexical-unit, senses, relations) — not the
empty legacy form-serializer output (spec §16.2 follow-up: the preview path was missed)."""
import pytest
from playwright.sync_api import Page


@pytest.mark.integration
@pytest.mark.playwright
def test_xml_preview_includes_alpine_lexical_unit(page: Page, app_url: str) -> None:
    page.goto(f"{app_url}/entries/add")
    page.wait_for_selector('#entry-form', timeout=10000)
    page.fill('input.lexical-unit-text', 'preview-test-word')
    page.wait_for_timeout(500)
    # Panel starts hidden; one click shows + generates.
    page.locator('#toggle-xml-preview-btn').click()
    page.wait_for_timeout(700)
    content = page.locator('#xml-preview-content').inner_text()
    assert 'Error generating XML' not in content, content[:200]
    assert 'preview-test-word' in content, "headword missing from XML preview: " + repr(content[:200])
