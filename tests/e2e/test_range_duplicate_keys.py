"""Regression: range dropdowns must render ALL options even when the flattened range
contains duplicate values.

Real LIFT/FieldWorks ranges are hierarchical and reuse range-element ids across the tree
(distinguished only by guid), so flattening produces duplicate `value`s. Alpine `x-for`
silently refuses to render a list with duplicate `:key` — keying range options on
`opt.value` drops the entire option list (the select shows only its placeholder).

The `grammatical-info` fixture (conftest `pristine_ranges_data`) is intentionally seeded with
a duplicate `Pronoun` id (one nested under `Pro-form`, one standalone). These tests fail if
any range x-for is keyed on `opt.value` instead of a unique `opt.key`. See spec §11.2.
"""
import pytest
from playwright.sync_api import Page


@pytest.mark.integration
@pytest.mark.playwright
def test_grammatical_info_fixture_has_duplicate_values(page: Page, app_url: str) -> None:
    """Guard the test data itself: the fixture must contain a duplicate flattened value,
    otherwise this whole regression is vacuous."""
    page.goto(f"{app_url}/entries/add")
    page.wait_for_selector('#entry-form', timeout=10000)
    page.wait_for_function(
        """() => {
            const el = document.querySelector('[x-data^="senseTree"]');
            if (!el || !window.Alpine) return false;
            const r = window.Alpine.$data(el).rangeData['grammatical-info'];
            return Array.isArray(r) && r.length > 0;
        }""",
        timeout=8000,
    )
    stats = page.evaluate("""() => {
        const opts = window.Alpine.$data(document.querySelector('[x-data^="senseTree"]'))
            .rangeData['grammatical-info'] || [];
        const vals = opts.map(o => o.value);
        return { total: vals.length, unique: new Set(vals).size };
    }""")
    assert stats["total"] > stats["unique"], (
        f"Fixture no longer contains duplicate range values ({stats}); the duplicate-key "
        f"regression test is meaningless. Re-add a duplicate id to grammatical-info."
    )


@pytest.mark.integration
@pytest.mark.playwright
def test_sense_range_select_renders_all_options_despite_duplicates(page: Page, app_url: str) -> None:
    """The sense Part-of-Speech select must render every option, even though the range
    flattens to duplicate values. With :key="opt.value" Alpine renders nothing."""
    page.goto(f"{app_url}/entries/add")
    page.wait_for_selector('#entry-form', timeout=10000)
    page.wait_for_function(
        """() => {
            const el = document.querySelector('[x-data^="senseTree"]');
            if (!el || !window.Alpine) return false;
            const r = window.Alpine.$data(el).rangeData['grammatical-info'];
            return Array.isArray(r) && r.length > 0;
        }""",
        timeout=8000,
    )
    result = page.evaluate("""() => {
        const d = window.Alpine.$data(document.querySelector('[x-data^="senseTree"]'));
        const rangeLen = (d.rangeData['grammatical-info'] || []).length;
        const sel = document.querySelector('.sense-grammatical-info-select');
        // dynamic options = all <option> minus the static "Select part of speech" placeholder
        const dynamicOptions = sel.querySelectorAll('option').length - 1;
        return { rangeLen, dynamicOptions };
    }""")
    assert result["dynamicOptions"] == result["rangeLen"], (
        f"Range select dropped options (rendered {result['dynamicOptions']} of "
        f"{result['rangeLen']}). A range x-for is keyed on opt.value (duplicate :key); "
        f"key on opt.key instead. See spec §11.2."
    )
    # Sanity: 'Pronoun' (the duplicated value) must actually appear as an option.
    assert page.locator('.sense-grammatical-info-select option', has_text='Pronoun').count() >= 1
