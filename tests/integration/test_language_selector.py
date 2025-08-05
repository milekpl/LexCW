import pytest
from playwright.sync_api import sync_playwright

@pytest.mark.integration
def test_language_selector_shows_only_configured_languages():
    """Test that the language selector only shows languages configured in project settings."""
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()

        # Navigate to the entry form
        page.goto("http://localhost:5000/entry/new")

        # Mock project settings to only include 'en' and 'pl'
        page.evaluate("""
            window.localStorage.setItem('projectSettings', JSON.stringify({
                source_language: { code: 'en', name: 'English' },
                target_languages: [{ code: 'pl', name: 'Polish' }]
            }));
        """)

        # Reload the page to apply mocked settings
        page.reload()

        # Check that only 'en' and 'pl' are available in the language selector
        language_options = page.locator("select.language-select option")
        assert language_options.count() == 2
        assert language_options.nth(0).get_attribute("value") == "en"
        assert language_options.nth(1).get_attribute("value") == "pl"

        browser.close()

@pytest.mark.integration
def test_language_selector_shows_warning_for_unconfigured_languages():
    """Test that a validation warning is shown for unconfigured languages."""
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()

        # Navigate to the entry form
        page.goto("http://localhost:5000/entry/new")

        # Mock project settings to only include 'en'
        page.evaluate("""
            window.localStorage.setItem('projectSettings', JSON.stringify({
                source_language: { code: 'en', name: 'English' },
                target_languages: []
            }));
        """)

        # Reload the page to apply mocked settings
        page.reload()

        # Simulate selecting an unconfigured language
        page.locator("select.language-select").select_option("fr")

        # Check that a validation warning is shown
        assert page.locator(".validation-warnings").is_visible()
        assert "Language 'fr' is not configured for this project" in page.locator(".validation-warnings").inner_text()

        browser.close()
