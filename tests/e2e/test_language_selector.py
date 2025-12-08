import pytest
from playwright.sync_api import Page
from flask import Flask

@pytest.mark.integration
def test_language_selector_shows_only_configured_languages(page: Page, flask_test_server, app: Flask):
    """Test that the language selector only shows languages configured in project settings.
    
    Note: The test database is configured with 'en' (English) as source and 'es' (Spanish) as target.
    We test against these default settings since the flask_test_server runs in a subprocess
    and cannot be reconfigured mid-test.
    """
    page = page

    # Navigate to the entry form
    page.goto(f"{flask_test_server}/entries/add")
    
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
@pytest.mark.skip(reason="Validation warnings for unconfigured languages not yet implemented")
def test_language_selector_shows_warning_for_unconfigured_languages(page: Page, flask_test_server, app: Flask):
    """Test that a validation warning is shown for unconfigured languages."""
    page = page
    
    # Configure project settings to only include 'en'
    with app.app_context():
        app.config_manager.set_source_language('en', 'English')
        app.config_manager.set_target_languages([])

    # Navigate to the entry form
    page.goto(f"{flask_test_server}/entries/add")

    # Wait for page to load
    page.wait_for_selector("select.language-select")

    # Simulate selecting an unconfigured language (if there was one in the list)
    # This test assumes we would show validation warnings for languages
    # that aren't in the configured set - but currently we only show configured languages
    # So this test needs the feature to be implemented first
    pass
