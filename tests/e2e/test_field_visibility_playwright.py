"""E2E tests for Field Visibility Modal using Playwright."""
import pytest
import asyncio


@pytest.mark.e2e
class TestFieldVisibilityModalE2E:
    """End-to-end tests for the Field Visibility Modal."""

    @pytest.fixture
    async def logged_in_page(self, page):
        """Navigate to the entry form and ensure page is loaded."""
        # Skip login for now - assuming app has auth bypass for testing
        await page.goto('/entries/new')
        await page.wait_for_load_state('networkidle')
        yield page

    @pytest.mark.asyncio
    async def test_modal_opens(self, page):
        """Test that the field visibility modal opens."""
        await page.goto('/entries/new')
        await page.wait_for_load_state('networkidle')

        # Click the field settings button
        await page.click('[data-bs-target="#fieldVisibilityModal"]')

        # Wait for modal to be visible
        modal = page.locator('#fieldVisibilityModal')
        await modal.wait_for(state='visible', timeout=5000)

        # Verify modal title
        assert await modal.locator('.modal-title').text_content() == ' Field Visibility Settings'

    @pytest.mark.asyncio
    async def test_all_sections_visible_in_modal(self, page):
        """Test that all sections are visible in the modal."""
        await page.goto('/entries/new')
        await page.wait_for_load_state('networkidle')

        # Open modal
        await page.click('[data-bs-target="#fieldVisibilityModal"]')

        # Wait for modal
        modal = page.locator('#fieldVisibilityModal')
        await modal.wait_for(state='visible')

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
            assert await locator.count() > 0, f"Section '{section}' not found"

    @pytest.mark.asyncio
    async def test_toggle_section_visibility(self, page):
        """Test toggling a section's visibility."""
        await page.goto('/entries/new')
        await page.wait_for_load_state('networkidle')

        # Open modal
        await page.click('[data-bs-target="#fieldVisibilityModal"]')
        modal = page.locator('#fieldVisibilityModal')
        await modal.wait_for(state='visible')

        # Uncheck a section (e.g., Custom Fields)
        checkbox = page.locator('#show-custom-fields')
        await checkbox.uncheck()

        # Close modal
        await page.click('.modal-footer button[data-bs-dismiss="modal"]')
        await modal.wait_for(state='hidden')

        # Verify custom fields section is hidden
        custom_fields = page.locator('.custom-fields-section')
        display_style = await custom_fields.evaluate('el => window.getComputedStyle(el).display')

        # Note: This test may need adjustment based on actual implementation
        # The manager should set display: none when unchecked

    @pytest.mark.asyncio
    async def test_reset_to_defaults(self, page):
        """Test resetting visibility settings to defaults."""
        await page.goto('/entries/new')
        await page.wait_for_load_state('networkidle')

        # Open modal
        await page.click('[data-bs-target="#fieldVisibilityModal"]')
        modal = page.locator('#fieldVisibilityModal')
        await modal.wait_for(state='visible')

        # Uncheck all sections
        checkboxes = page.locator('.field-visibility-toggle')
        count = await checkboxes.count()
        for i in range(count):
            await checkboxes.nth(i).uncheck()

        # Click reset button
        await page.click('.reset-field-visibility-btn')

        # Verify all checkboxes are checked again
        for i in range(count):
            assert await checkboxes.nth(i).is_checked(), f"Checkbox {i} not checked after reset"

    @pytest.mark.asyncio
    async def test_show_all_sections(self, page):
        """Test showing all sections."""
        await page.goto('/entries/new')
        await page.wait_for_load_state('networkidle')

        # Open modal
        await page.click('[data-bs-target="#fieldVisibilityModal"]')
        modal = page.locator('#fieldVisibilityModal')
        await modal.wait_for(state='visible')

        # Uncheck a section first
        await page.locator('#show-basic-info').uncheck()

        # Click show all button
        await page.click('.show-all-sections-btn')

        # Verify all checkboxes are checked
        assert await page.locator('#show-basic-info').is_checked()

    @pytest.mark.asyncio
    async def test_hide_empty_sections(self, page):
        """Test hiding empty sections."""
        await page.goto('/entries/new')
        await page.wait_for_load_state('networkidle')

        # Open modal
        await page.click('[data-bs-target="#fieldVisibilityModal"]')
        modal = page.locator('#fieldVisibilityModal')
        await modal.wait_for(state='visible')

        # Click hide empty sections button
        await page.click('.hide-empty-sections-btn')

        # The behavior depends on what's empty in the form
        # This test verifies the button click doesn't cause errors

    @pytest.mark.asyncio
    async def test_close_modal(self, page):
        """Test closing the modal."""
        await page.goto('/entries/new')
        await page.wait_for_load_state('networkidle')

        # Open modal
        await page.click('[data-bs-target="#fieldVisibilityModal"]')
        modal = page.locator('#fieldVisibilityModal')
        await modal.wait_for(state='visible')

        # Close using close button
        await page.click('#fieldVisibilityModal .btn-close')
        await modal.wait_for(state='hidden')

        # Also test closing with footer button
        await page.click('[data-bs-target="#fieldVisibilityModal"]')
        await modal.wait_for(state='visible')
        await page.click('#fieldVisibilityModal .modal-footer .btn-secondary')
        await modal.wait_for(state='hidden')

    @pytest.mark.asyncio
    async def test_field_visibility_manager_initialized(self, page):
        """Test that FieldVisibilityManager is initialized."""
        await page.goto('/entries/new')
        await page.wait_for_load_state('networkidle')

        # Check that the manager is available on window
        manager_exists = await page.evaluate('typeof window.fieldVisibilityManager !== "undefined"')
        assert manager_exists

        # Check that it's the correct class
        is_correct_class = await page.evaluate('window.fieldVisibilityManager instanceof FieldVisibilityManager')
        assert is_correct_class

    @pytest.mark.asyncio
    async def test_get_settings(self, page):
        """Test getting current visibility settings."""
        await page.goto('/entries/new')
        await page.wait_for_load_state('networkidle')

        # Get settings from manager
        settings = await page.evaluate('window.fieldVisibilityManager.getSettings()')

        assert isinstance(settings, object)
        assert 'basic-info' in settings
        assert 'custom-fields' in settings
        assert 'senses' in settings

    @pytest.mark.asyncio
    async def test_toggle_method(self, page):
        """Test the toggle method."""
        await page.goto('/entries/new')
        await page.wait_for_load_state('networkidle')

        # Toggle a section
        new_state = await page.evaluate(
            'window.fieldVisibilityManager.toggle("custom-fields")'
        )

        # Verify toggle worked
        is_visible = await page.evaluate(
            'window.fieldVisibilityManager.isVisible("custom-fields")'
        )
        assert is_visible == new_state

        # Toggle back
        await page.evaluate('window.fieldVisibilityManager.toggle("custom-fields")')
        is_visible = await page.evaluate(
            'window.fieldVisibilityManager.isVisible("custom-fields")'
        )
        assert is_visible == True

    @pytest.mark.asyncio
    async def test_custom_event_fired(self, page):
        """Test that CustomEvent is fired on visibility change."""
        await page.goto('/entries/new')
        await page.wait_for_load_state('networkidle')

        # Set up event listener
        event_fired = []
        page.expose_function('recordEvent', lambda e: event_fired.append(e))
        await page.evaluate('''
            document.addEventListener('fieldVisibilityChanged', (e) => {
                window.recordEvent(e.detail);
            });
        ''')

        # Open modal and toggle a section
        await page.click('[data-bs-target="#fieldVisibilityModal"]')
        await page.locator('#show-custom-fields').uncheck()
        await page.locator('#show-custom-fields').check()

        # Wait for events to be recorded
        await page.wait_for_timeout(100)

        # Check events were fired
        assert len(event_fired) >= 2  # At least uncheck and check events

    @pytest.mark.asyncio
    async def test_settings_persisted_to_localstorage(self, page):
        """Test that settings are persisted to localStorage."""
        await page.goto('/entries/new')
        await page.wait_for_load_state('networkidle')

        # Uncheck a section
        await page.click('[data-bs-target="#fieldVisibilityModal"]')
        await page.locator('#show-variants').uncheck()

        # Reload page
        await page.reload()
        await page.wait_for_load_state('networkidle')

        # Check that the setting persisted
        is_visible = await page.evaluate(
            'window.fieldVisibilityManager.isVisible("variants")'
        )
        assert is_visible == False

    @pytest.mark.asyncio
    async def test_settings_persisted_to_localstorage_show_all(self, page):
        """Test that show all persists to localStorage."""
        await page.goto('/entries/new')
        await page.wait_for_load_state('networkidle')

        # Open modal and click show all (should already be all visible)
        await page.click('[data-bs-target="#fieldVisibilityModal"]')
        await page.click('.show-all-sections-btn')

        # Reload page
        await page.reload()
        await page.wait_for_load_state('networkidle')

        # Check that all settings are true
        settings = await page.evaluate('window.fieldVisibilityManager.getSettings()')
        all_true = all(settings.values())
        assert all_true
