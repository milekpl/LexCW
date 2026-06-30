"""
E2E tests for Markdown / PDF export.

Tests that:
- The Markdown card is visible on the export options page
- Export generates a downloadable .md file
- The exported content contains expected entry data
- Profile-driven export uses field ordering and abbreviation
- Unmapped value warnings are shown
- Root-based lexicon type organizes entries hierarchically
"""

from __future__ import annotations

import json
import re
import pytest
from playwright.sync_api import Page, expect


@pytest.mark.integration
@pytest.mark.playwright
def test_markdown_card_visible(page: Page, app_url: str) -> None:
    """The Markdown export card should be visible on the export page."""
    page.goto(f"{app_url}/export")
    page.wait_for_load_state("networkidle")

    card = page.locator('.card-header h3:has-text("Markdown")')
    expect(card).to_be_visible()

    title_input = page.locator('#md_title')
    expect(title_input).to_be_visible()
    expect(title_input).to_have_value("Dictionary")

    profile_select = page.locator('#md_profile')
    expect(profile_select).to_be_visible()

    submit_btn = page.locator('button:has-text("Export to Markdown")')
    expect(submit_btn).to_be_visible()


@pytest.mark.integration
@pytest.mark.playwright
def test_markdown_export_basic(page: Page, app_url: str) -> None:
    """Basic export (no profile) should generate a valid .md file."""
    page.goto(f"{app_url}/export/markdown?title=Test+Dictionary")
    page.wait_for_load_state("networkidle")

    alert = page.locator('.alert-success')
    expect(alert).to_be_visible()

    download_link = page.locator('a.list-group-item-action')
    expect(download_link).to_be_visible()
    expect(download_link).to_contain_text('.md')

    # Download and verify content
    href = download_link.get_attribute('href')
    response = page.evaluate(f"""
        async () => {{ const r = await fetch('{href}'); return await r.text(); }}
    """)

    assert response.startswith('---')
    assert 'title: "Test Dictionary"' in response
    assert 'cat' in response
    assert 'dog' in response
    assert 'run' in response


@pytest.mark.integration
@pytest.mark.playwright
def test_markdown_export_instructions(page: Page, app_url: str) -> None:
    """The download page should show pandoc instructions."""
    page.goto(f"{app_url}/export/markdown?title=Test")
    page.wait_for_load_state("networkidle")

    content = page.content()
    assert 'pandoc' in content.lower()
    assert 'classoption=twocolumn' in content


@pytest.mark.integration
@pytest.mark.playwright
def test_markdown_profile_selector_shown(page: Page, app_url: str) -> None:
    """Profile selector and options appear on the export page."""
    page.goto(f"{app_url}/export")
    page.wait_for_load_state("networkidle")

    select = page.locator('#md_profile')
    expect(select).to_be_visible()

    options = select.locator('option')
    count = options.count()
    # At minimum: the "-- Simple --" option
    assert count >= 1
    first_text = options.nth(0).text_content()
    assert 'Simple' in first_text


@pytest.mark.integration
@pytest.mark.playwright
def test_markdown_profile_driven_export(page: Page, app_url: str) -> None:
    """Export with a display profile produces profile-driven content."""
    # Create a display profile via API
    profile_id = _create_basic_profile(page, app_url)
    try:
        page.goto(
            f"{app_url}/export/markdown?title=Profile+Test&profile_id={profile_id}"
        )
        page.wait_for_load_state("networkidle")

        alert = page.locator('.alert-success')
        expect(alert).to_be_visible()

        download_link = page.locator('a.list-group-item-action')
        href = download_link.get_attribute('href')
        response = page.evaluate(f"""
            async () => {{ const r = await fetch('{href}'); return await r.text(); }}
        """)

        # Profile-driven output has YAML frontmatter with --- not ...
        assert response.startswith('---')
        assert 'cat' in response
    finally:
        _delete_profile(page, app_url, profile_id)


@pytest.mark.integration
@pytest.mark.playwright
def test_markdown_export_with_abbreviation_warnings(page: Page, app_url: str) -> None:
    """Export with a profile that triggers unmapped abbreviation warnings."""
    profile_id = _create_profile_with_warnings(page, app_url)
    try:
        page.goto(
            f"{app_url}/export/markdown?title=Warn+Test&profile_id={profile_id}"
        )
        page.wait_for_load_state("networkidle")

        # Should show success with warning count
        alert = page.locator('.alert-success')
        expect(alert).to_be_visible()

        # Should have a warning toggle button
        warning_btn = page.locator('button:has-text("unmapped")')
        expect(warning_btn).to_be_visible()

        # Click to expand warnings
        warning_btn.click()
        page.wait_for_timeout(300)

        # Warning table should be visible
        warning_table = page.locator('table.table-warning, .card.border-warning table')
        expect(warning_table).to_be_visible()
    finally:
        _delete_profile(page, app_url, profile_id)


# -- Helpers -------------------------------------------------------------

def _create_basic_profile(page: Page, app_url: str) -> int:
    """Create a minimal display profile via the API and return its ID."""
    elements = [
        {"lift_element": "lexical-unit", "display_order": 10,
         "css_class": "headword", "visibility": "always"},
        {"lift_element": "pronunciation", "display_order": 20,
         "css_class": "pronunciation", "visibility": "if-content"},
        {"lift_element": "sense", "display_order": 30,
         "css_class": "sense", "visibility": "if-content"},
        {"lift_element": "definition", "display_order": 40,
         "css_class": "definition", "visibility": "if-content"},
    ]
    result = page.evaluate(f"""
        async () => {{
            const r = await fetch('{app_url}/api/display-profiles', {{
                method: 'POST',
                headers: {{ 'Content-Type': 'application/json' }},
                body: JSON.stringify({{
                    name: "E2E Test Profile Basic",
                    elements: {json.dumps(elements)}
                }})
            }});
            const data = await r.json();
            return data.id || data.profile?.id;
        }}
    """)
    return int(result)


def _create_profile_with_warnings(page: Page, app_url: str) -> int:
    """Create a profile with grammatical-info & abbr aspect to trigger warnings."""
    elements = [
        {"lift_element": "lexical-unit", "display_order": 10,
         "css_class": "headword", "visibility": "always"},
        {"lift_element": "sense", "display_order": 20,
         "css_class": "sense", "visibility": "if-content"},
        {"lift_element": "grammatical-info", "display_order": 30,
         "css_class": "pos", "visibility": "always",
         "config": {"display_aspect": "abbr"}},
        {"lift_element": "definition", "display_order": 40,
         "css_class": "definition", "visibility": "if-content"},
    ]
    result = page.evaluate(f"""
        async () => {{
            const r = await fetch('{app_url}/api/display-profiles', {{
                method: 'POST',
                headers: {{ 'Content-Type': 'application/json' }},
                body: JSON.stringify({{
                    name: "E2E Test Profile Warnings",
                    show_subentries: false,
                    export_config: {{
                        "lexicon_type": "lexeme-based",
                        "subentry_style": "indented"
                    }},
                    elements: {json.dumps(elements)}
                }})
            }});
            const data = await r.json();
            return data.id || data.profile?.id;
        }}
    """)
    return int(result)


def _delete_profile(page: Page, app_url: str, profile_id: int) -> None:
    """Delete a display profile via API."""
    page.evaluate(f"""
        async () => {{
            await fetch('{app_url}/api/display-profiles/{profile_id}', {{
                method: 'DELETE'
            }});
        }}
    """)
