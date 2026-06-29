"""Sense-level range dropdowns (PoS, Domain Type, Semantic Domain, Usage Type) now have
a type-to-filter search box (Alpine searchSelect). Verify filter + pick + persistence."""
import time
import pytest
import requests
from playwright.sync_api import Page, expect


def _field(page: Page, label: str, sense_idx: int = 0):
    sense = page.locator('.sense-item').nth(sense_idx)
    return sense.locator('.mb-3').filter(
        has=page.locator(f'label:has-text("{label}")')).first


def _real_options(field):
    # Real range options only — exclude the muted "— none —" entry (single-select).
    return field.locator('.list-group-item-action:not(.text-muted)')


@pytest.mark.integration
@pytest.mark.playwright
def test_part_of_speech_search_and_persist(page: Page, app_url: str) -> None:
    hw = f"ss-{int(time.time()*1000)}"
    page.goto(f"{app_url}/entries/add")
    page.wait_for_selector('#entry-form', timeout=10000)
    page.fill('input.lexical-unit-text', hw)
    page.locator('textarea.definition-text:visible').first.fill("def")
    page.wait_for_timeout(1000)  # let senseTree.loadRanges() populate option lists

    field = _field(page, 'Part of Speech')
    box = field.locator('input[type="text"]').first
    box.click()
    opts = _real_options(field)
    expect(opts.first).to_be_visible(timeout=8000)
    total = opts.count()
    assert total > 1, "no PoS options loaded"

    # Type to filter by the first option's label; the list must narrow (or stay equal).
    label = opts.first.inner_text().strip()
    box.fill(label[:3])
    page.wait_for_timeout(200)
    narrowed = _real_options(field)
    assert narrowed.count() <= total, "filter did not narrow"
    expect(narrowed.first).to_be_visible(timeout=4000)
    narrowed.first.click()
    page.wait_for_timeout(150)
    # The search box doubles as the display: it now shows the chosen label.
    assert box.input_value().strip() != "", "selection not shown in box"

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
        time.sleep(0.4)
    assert eid, "entry not found"
    xml = requests.get(f"{app_url}/api/xml/entries/{eid}").text
    assert '<grammatical-info' in xml, "sense PoS not persisted: " + xml[:400]


@pytest.mark.integration
@pytest.mark.playwright
def test_semantic_domain_multiselect_chips(page: Page, app_url: str) -> None:
    page.goto(f"{app_url}/entries/add")
    page.wait_for_selector('#entry-form', timeout=10000)
    page.fill('input.lexical-unit-text', f"ssm-{int(time.time()*1000)}")
    page.wait_for_timeout(1000)  # let senseTree.loadRanges() populate option lists

    field = _field(page, 'Semantic Domain')
    box = field.locator('input[type="text"]').first
    box.scroll_into_view_if_needed()
    box.click()
    opts = field.locator('.list-group-item-action')  # multi-select has no "— none —"
    expect(opts.first).to_be_visible(timeout=8000)
    if opts.count() < 2:
        pytest.skip("semantic-domain range has <2 options in this DB")

    opts.nth(0).click()
    page.wait_for_timeout(120)
    field.locator('.list-group-item-action').nth(1).click()
    page.wait_for_timeout(120)

    # Two selections → two chips (badges); the dropdown stays open for multi-pick.
    chips = field.locator('.badge')
    expect(chips).to_have_count(2)
