import pytest
from playwright.sync_api import Page
from flask import Flask

@pytest.mark.integration
def test_language_selector_shows_only_configured_languages(playwright_page: Page, live_server, app: Flask):
    """Test that the language selector only shows languages configured in project settings."""
    page = playwright_page
    
    # Configure project settings to only include 'en' and 'pl'
    with app.app_context():
        app.config_manager.set_source_language('en', 'English')
        app.config_manager.set_target_languages([{'code': 'pl', 'name': 'Polish'}])

    # Navigate to the entry form
    page.goto(f"{live_server.url}/entries/add")
    
    # Wait for page to load
    page.wait_for_selector("select.language-select")

    # Check the first language selector (for definition)
    first_selector = page.locator("select.language-select").first
    language_options = first_selector.locator("option")
    
    # Should have 2 languages: en and pl
    assert language_options.count() == 2
    
    # Get the option values
    option_values = [language_options.nth(i).get_attribute("value") for i in range(language_options.count())]
    assert 'en' in option_values
    assert 'pl' in option_values

@pytest.mark.integration  
@pytest.mark.skip(reason="Validation warnings for unconfigured languages not yet implemented")
def test_language_selector_shows_warning_for_unconfigured_languages(playwright_page: Page, live_server, app: Flask):
    """Test that a validation warning is shown for unconfigured languages."""
    page = playwright_page
    
    # Configure project settings to only include 'en'
    with app.app_context():
        app.config_manager.set_source_language('en', 'English')
        app.config_manager.set_target_languages([])

    # Navigate to the entry form
    page.goto(f"{live_server.url}/entries/add")

    # Wait for page to load
    page.wait_for_selector("select.language-select")

    # Simulate selecting an unconfigured language (if there was one in the list)
    # This test assumes we would show validation warnings for languages
    # that aren't in the configured set - but currently we only show configured languages
    # So this test needs the feature to be implemented first
    pass
