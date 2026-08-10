import time
import pytest
from playwright.sync_api import Page, expect
from flask import Flask


@pytest.mark.integration
def test_language_selector_shows_only_configured_languages(page: Page, app_url: str, configured_flask_app):
    """Test that the language selector only shows languages configured in project settings.

    Note: The test database is configured with 'en' (English) as source and 'es' (Spanish) as target.
    We test against these default settings since the flask_test_server runs in a subprocess
    and cannot be reconfigured mid-test.
    """
    # Navigate to the entry form
    page.goto(f"{app_url}/entries/add")

    # Wait for page to load
    page.wait_for_selector("select.language-select")

    # Check the first language selector (for definition)
    first_selector = page.locator("select.language-select").first
    language_options = first_selector.locator("option")

    # Should have 2 languages: en (source) and es (target)
    assert language_options.count() == 2

    # Get the option values
    option_values = [language_options.nth(i).get_attribute("value") for i in range(language_options.count())]
    assert 'en' in option_values, f"Expected 'en' in language options, got: {option_values}"
    assert 'es' in option_values, f"Expected 'es' in language options, got: {option_values}"

@pytest.mark.integration
@pytest.mark.integration
def test_language_selector_shows_warning_for_unconfigured_languages(page: Page, app_url: str, configured_flask_app):
    """Test that a validation warning is shown for unconfigured languages.

    The configured project has source 'en' and no target languages, so an entry
    with an 'fr' gloss should surface the "Unconfigured language" warning in the
    senses section (the sense tree flags any language code not in the project's
    configured set).
    """
    import requests

    # Create an entry with an 'fr' gloss (fr is NOT configured: source=en, targets=[])
    headword = f"langwarn-{int(time.time() * 1000)}"
    resp = requests.post(
        f"{app_url}/api/entries/",
        json={
            "lexical_unit": {"en": headword},
            "senses": [{"definition": {"en": "def"}, "glosses": {"fr": "sens"}}],
        },
    )
    assert resp.ok, resp.text
    entry_id = resp.json().get("id")
    assert entry_id

    # Open the edit form — the senses section should warn about 'fr'
    page.goto(f"{app_url}/entries/{entry_id}/edit")
    page.wait_for_selector('#entry-form', state='visible', timeout=10000)

    warning = page.locator('.unconfigured-languages-warning')
    expect(warning.first).to_be_visible(timeout=8000)
    text = warning.first.inner_text()
    assert 'fr' in text, f"Expected 'fr' in the unconfigured-languages warning, got: {text}"
