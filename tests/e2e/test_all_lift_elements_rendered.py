"""Sanity test (spec §14.4): every editable LIFT element renders a field in the entry form.

The Alpine migration moved many fields between templates/components; nothing else proves a
field wasn't silently dropped. This test is driven from the registry
(``app/data/lift_elements.json``) so it cannot drift: every registry element must be either
**mapped** to a rendered selector (asserted present) or **explicitly excluded** with a reason.
Adding a new LIFT element to the registry will fail this test until it is triaged here.
"""
import json
import os

import pytest
from playwright.sync_api import Page

_REGISTRY = os.path.join(
    os.path.dirname(__file__), '..', '..', 'app', 'data', 'lift_elements.json')


def _registry_element_names():
    with open(_REGISTRY) as f:
        return {e['name'] for e in json.load(f)['elements']}


# Editable element -> a selector that must be present in the rendered add-entry form.
# (Some appear only after a setup action; see SETUP_ACTIONS / per-element notes below.)
MAPPED = {
    'lexical-unit':     'input.lexical-unit-text',
    'citation':         '#citation-form',
    'pronunciation':    '#add-pronunciation-btn',
    'variant':          '.variants-section',
    'sense':            '.sense-item',
    'subsense':         '.add-subsense-btn',
    'grammatical-info': '.sense-grammatical-info-select',
    'gloss':            '[data-field-id="sense-gloss"]',
    'definition':       'textarea.definition-text',
    'example':          'button.add-example-btn',
    'reversal':         '.add-reversal-btn',       # ported into senseTree (§16.1)
    'illustration':     '.add-illustration-btn',   # regression re-added (§16.1)
    'relation':         '.relations-section',
    'variant-relation': '.direct-variants-section',
    'etymology':        '#add-etymology-btn',
    'note':             '#add-note-btn',
    'annotation':       '.annotations-section-entry',
    'translation':      '.example-translation-text',  # after adding an example
}

# Structural / inline / on-demand elements that are NOT a standalone form field — each with the
# reason it is excluded. Together with MAPPED these must cover EVERY registry element.
EXCLUDED = {
    'entry': 'root container, not a field',
    'trait': 'rendered AS the range-backed selects (grammatical-info, domain/semantic/usage)',
    'form':  'building block of every multilingual field (form>text), not standalone',
    'text':  'inner text node of <form>',
    'span':  'inline annotation markup inside text, not a form field',
    'media': 'pronunciation audio / illustration media, nested in those sections',
    'label': 'inner label of illustrations / range elements',
    'caption': 'inner caption of illustration media',
    'main':  'reversal <main> child, nested inside reversal',
    'field': 'custom fields are display-only and render only when entry.custom_fields exists '
             '({% if entry.custom_fields %}); there is no add control on a new entry (this '
             'predates the Alpine migration).',
}


@pytest.mark.integration
@pytest.mark.playwright
def test_registry_fully_triaged():
    """Guard: every registry element is either mapped to a field or explicitly excluded.
    A new LIFT element forces a decision here (this is what makes it an 'all elements' check)."""
    names = _registry_element_names()
    covered = set(MAPPED) | set(EXCLUDED)
    missing = names - covered
    assert not missing, (
        f"LIFT elements not triaged in the sanity test: {sorted(missing)}. "
        f"Add each to MAPPED (with a selector) or EXCLUDED (with a reason).")
    # Also catch stale entries that no longer exist in the registry.
    stale = covered - names
    assert not stale, f"Sanity-test entries no longer in the registry: {sorted(stale)}"


@pytest.mark.integration
@pytest.mark.playwright
def test_all_editable_elements_render(page: Page, app_url: str) -> None:
    page.goto(f"{app_url}/entries/add")
    page.wait_for_selector('#entry-form', timeout=10000)
    page.wait_for_selector('.sense-item', timeout=8000)  # seeded sense

    # Render the on-demand sections so their fields exist.
    page.fill('input.lexical-unit-text', 'sanity_entry')
    page.locator('textarea.definition-text:visible').first.fill('def')
    page.locator('button.add-example-btn').first.click()   # -> translation row
    page.wait_for_timeout(400)

    missing = []
    for element, selector in sorted(MAPPED.items()):
        if page.locator(selector).count() == 0:
            missing.append(f"{element} ({selector})")
    assert not missing, "LIFT elements with no rendered field: " + "; ".join(missing)
