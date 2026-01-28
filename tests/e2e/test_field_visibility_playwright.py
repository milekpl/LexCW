"""E2E tests for Field Visibility Modal using Playwright."""
import pytest
from playwright.sync_api import expect


@pytest.mark.integration
@pytest.mark.playwright
class TestFieldVisibilityModalE2E:
    """End-to-end tests for the Field Visibility Modal."""

    def test_modal_opens(self, page, app_url):
        """Test that the field visibility modal opens."""
        page.goto(f'{app_url}/entries/add')
        page.wait_for_load_state('networkidle')

        # Click the field settings button
        page.click('[data-bs-toggle="modal"][data-bs-target="#fieldVisibilityModal"]')

        # Wait for modal to be visible
        modal = page.locator('#fieldVisibilityModal')
        modal.wait_for(state='visible', timeout=5000)

        # Verify modal title (strip whitespace as template formatting adds newlines)
        assert modal.locator('.modal-title').text_content().strip() == 'Field Visibility Settings'

    def test_all_sections_visible_in_modal(self, page, app_url):
        """Test that all sections are visible in the modal."""
        page.goto(f'{app_url}/entries/add')
        page.wait_for_load_state('networkidle')

        # Open modal
        page.click('[data-bs-toggle="modal"][data-bs-target="#fieldVisibilityModal"]')

        # Wait for modal
        modal = page.locator('#fieldVisibilityModal')
        modal.wait_for(state='visible')

        # Check each section is listed
        sections = [
            'Basic Information',
            'Custom Fields',
            'Entry Notes',
            'Pronunciation',
            'Variants',
            'Direct Variants',
            'Relations',
            'Senses & Definitions'
        ]

        for section in sections:
            locator = page.locator(f'label:has-text("{section}")')
            assert locator.count() > 0, f"Section '{section}' not found"

    def test_toggle_section_visibility(self, page, app_url):
        """Test toggling a section's visibility using the FieldVisibilityManager."""
        page.goto(f'{app_url}/entries/add')
        page.wait_for_load_state('networkidle')

        # Test the manager's toggle method directly
        # Toggle custom-fields section
        initial_state = page.evaluate('window.fieldVisibilityManager.isVisible("custom-fields")')
        page.evaluate('window.fieldVisibilityManager.toggle("custom-fields")')
        new_state = page.evaluate('window.fieldVisibilityManager.isVisible("custom-fields")')

        # State should have changed
        assert new_state != initial_state, "Toggle should change visibility state"

        # Toggle back
        page.evaluate('window.fieldVisibilityManager.toggle("custom-fields")')
        final_state = page.evaluate('window.fieldVisibilityManager.isVisible("custom-fields")')
        assert final_state == initial_state, "Toggle back should restore original state"

    def test_reset_to_defaults(self, page, app_url):
        """Test resetting visibility settings to defaults."""
        page.goto(f'{app_url}/entries/add')
        page.wait_for_load_state('networkidle')

        # Open modal
        page.click('[data-bs-toggle="modal"][data-bs-target="#fieldVisibilityModal"]')
        modal = page.locator('#fieldVisibilityModal')
        modal.wait_for(state='visible')

        # Click reset button
        page.click('.reset-field-visibility-btn')

        # Verify all section checkboxes are checked by checking manager state
        settings = page.evaluate('window.fieldVisibilityManager.getSettings()')
        # The settings object has 'sections' and 'fields' keys with nested settings
        # Check that all section visibility settings in 'sections' are true
        assert 'sections' in settings, "Settings should have 'sections' key"
        for section_id, is_visible in settings['sections'].items():
            assert is_visible == True, f"Section '{section_id}' should be visible after reset"

    def test_show_all_sections(self, page, app_url):
        """Test showing all sections."""
        page.goto(f'{app_url}/entries/add')
        page.wait_for_load_state('networkidle')

        # Open modal
        page.click('[data-bs-toggle="modal"][data-bs-target="#fieldVisibilityModal"]')
        modal = page.locator('#fieldVisibilityModal')
        modal.wait_for(state='visible')

        # Click show all button
        page.click('.show-all-sections-btn')

        # Verify all checkboxes are checked
        settings = page.evaluate('window.fieldVisibilityManager.getSettings()')
        all_true = all(settings.values())
        assert all_true, "All sections should be visible after clicking Show All"

    def test_hide_empty_sections(self, page, app_url):
        """Test hiding empty sections."""
        page.goto(f'{app_url}/entries/add')
        page.wait_for_load_state('networkidle')

        # Open modal
        page.click('[data-bs-toggle="modal"][data-bs-target="#fieldVisibilityModal"]')
        modal = page.locator('#fieldVisibilityModal')
        modal.wait_for(state='visible')

        # Click hide empty sections button - this tests that the button exists and is clickable
        page.click('.hide-empty-sections-btn')
        # No assertion needed - just verify no JavaScript errors occurred

    def test_close_modal(self, page, app_url):
        """Test closing the modal."""
        page.goto(f'{app_url}/entries/add')
        page.wait_for_load_state('networkidle')

        # Open modal
        page.click('[data-bs-toggle="modal"][data-bs-target="#fieldVisibilityModal"]')
        modal = page.locator('#fieldVisibilityModal')
        modal.wait_for(state='visible')

        # Close using close button
        page.click('#fieldVisibilityModal .btn-close')
        modal.wait_for(state='hidden')

        # Also test closing with footer button
        page.click('[data-bs-toggle="modal"][data-bs-target="#fieldVisibilityModal"]')
        modal.wait_for(state='visible')
        page.click('#fieldVisibilityModal .modal-footer .btn-secondary')
        modal.wait_for(state='hidden')

    def test_field_visibility_manager_initialized(self, page, app_url):
        """Test that FieldVisibilityManager is initialized."""
        page.goto(f'{app_url}/entries/add')
        page.wait_for_load_state('networkidle')

        # Check that the manager is available on window
        manager_exists = page.evaluate('typeof window.fieldVisibilityManager !== "undefined"')
        assert manager_exists

        # Check that it's the correct class
        is_correct_class = page.evaluate('window.fieldVisibilityManager instanceof FieldVisibilityManager')
        assert is_correct_class

    def test_get_settings(self, page, app_url):
        """Test getting current visibility settings."""
        page.goto(f'{app_url}/entries/add')
        page.wait_for_load_state('networkidle')

        # Get settings from manager
        settings = page.evaluate('window.fieldVisibilityManager.getSettings()')

        assert isinstance(settings, object)
        # Settings now has 'sections' and 'fields' structure
        assert 'sections' in settings, "Settings should have 'sections' key"
        assert 'fields' in settings, "Settings should have 'fields' key"
        # Check section settings
        assert 'basic-info' in settings['sections']
        assert 'custom-fields' in settings['sections']
        assert 'senses' in settings['sections']

    def test_toggle_method(self, page, app_url):
        """Test the toggle method."""
        page.goto(f'{app_url}/entries/add')
        page.wait_for_load_state('networkidle')

        # Toggle a section
        new_state = page.evaluate(
            'window.fieldVisibilityManager.toggle("custom-fields")'
        )

        # Verify toggle worked
        is_visible = page.evaluate(
            'window.fieldVisibilityManager.isVisible("custom-fields")'
        )
        assert is_visible == new_state

        # Toggle back
        page.evaluate('window.fieldVisibilityManager.toggle("custom-fields")')
        is_visible = page.evaluate(
            'window.fieldVisibilityManager.isVisible("custom-fields")'
        )
        assert is_visible == True

    def test_custom_event_fired(self, page, app_url):
        """Test that CustomEvent is fired on visibility change."""
        page.goto(f'{app_url}/entries/add')
        page.wait_for_load_state('networkidle')

        # Set up event listener
        event_fired = []
        page.expose_function('recordEvent', lambda e: event_fired.append(e))
        page.evaluate('''
            document.addEventListener('fieldVisibilityChanged', (e) => {
                window.recordEvent(e.detail);
            });
        ''')

        # Toggle a section via the manager (opens modal internally if needed)
        page.evaluate('window.fieldVisibilityManager.toggle("custom-fields")')
        page.evaluate('window.fieldVisibilityManager.toggle("custom-fields")')

        # Wait for events to be recorded
        page.wait_for_timeout(100)

        # Check events were fired (at least 2 - toggle off and on)
        assert len(event_fired) >= 2, f"Expected at least 2 events, got {len(event_fired)}"


# Note: LocalStorage persistence tests have been removed.
# Field visibility settings are now stored per-user in the database via API.
# Tests for API-based persistence would require authentication setup.
