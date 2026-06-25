"""
E2E Tests for Etymology Type Population
==========================================

Tests that the etymology type dropdown is correctly populated from LIFT ranges API.
This ensures lexicographers can select appropriate etymological categories when
editing dictionary entries.

Usage:
    pytest tests/e2e/test_etymology.py -v
"""

import pytest
from playwright.sync_api import expect


@pytest.mark.e2e
class TestEtymologyTypePopulation:
    """Test that etymology type dropdown is populated from LIFT ranges."""

    def test_etymology_type_dropdown_populated(self, page, app_url):
        """
        Verify etymology type dropdown contains values from the 'etymology' range.

        Steps:
            1. Navigate to entry form
            2. Click 'Add Etymology' button
            3. Verify type dropdown has values (inheritance, borrowing, compound, etc.)
        """
        # Navigate to create new entry
        page.goto(f"{app_url}/entries/add")
        page.wait_for_load_state('networkidle')

        # Wait for etymology section to be visible
        page.wait_for_selector('#etymology-container', state='visible')
        page.wait_for_selector('#add-etymology-btn', state='visible')

        # Click 'Add Etymology' button
        add_button = page.locator('#add-etymology-btn')
        expect(add_button).to_be_visible()
        add_button.click()

        # Wait for etymology form to appear
        page.wait_for_selector('.etymology-form-item', state='visible')

        # Find the type dropdown
        type_select = page.locator('.etymology-type-select').first
        expect(type_select).to_be_visible()

        # Wait for dynamic range options to load (populated asynchronously)
        page.wait_for_selector('.etymology-type-select option:not([value=""])', state='attached', timeout=10000)

        # Get all options
        options = type_select.locator('option').all_text_contents()

        # Verify expected etymology types are present (from LIFT ranges)
        expected_types = ['borrowed', 'proto']
        for etype in expected_types:
            assert any(etype in opt.lower() for opt in options), \
                f"Etymology type '{etype}' not found in dropdown options: {options}"

        print(f"✅ Etymology type dropdown populated with {len(options)} options")

    def test_etymology_type_selection_works(self, page, app_url):
        """
        Verify selected etymology type can be selected in the dropdown.

        (Save/redirect is tested separately in form save tests.
        This test focuses on the dropdown selection UI.)
        """
        # Create new entry
        page.goto(f"{app_url}/entries/add")
        page.wait_for_load_state('networkidle')

        # Fill basic entry data
        page.fill('input[name="lexical_unit.en"]', 'testword')

        # Add etymology
        page.click('#add-etymology-btn')
        page.wait_for_selector('.etymology-form-item', state='visible')

        # Wait for dynamic range options to load
        page.wait_for_selector('.etymology-type-select option:not([value=""])', state='attached', timeout=10000)
        # Select 'borrowed' type by label
        page.select_option('.etymology-type-select', label='borrowed')

        # Verify the selection was made
        selected_value = page.evaluate(
            "document.querySelector('.etymology-type-select')?.value"
        )
        assert selected_value, "No etymology type was selected"
        print(f"✅ Etymology type selected: {selected_value}")

        # Also verify source and form fields can be filled
        page.fill('input[name*="etymologies[0][source]"]', 'Latin')
        page.fill('input[name*="etymologies[0][form]"]', 'testum')
        source = page.input_value('input[name*="etymologies[0][source]"]')
        assert source == 'Latin', "Source language field not filled correctly"
        print("✅ Etymology form fields work correctly")
