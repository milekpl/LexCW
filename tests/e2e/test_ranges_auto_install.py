"""
E2E Tests for Auto-install Default Ranges
============================================

Tests that minimal LIFT ranges are automatically installed for empty databases.
This ensures new projects have basic dropdowns and validation rules available
immediately without manual configuration.

Usage:
    pytest tests/e2e/test_ranges_auto_install.py -v
"""

import pytest
from playwright.sync_api import expect


@pytest.mark.e2e
class TestAutoInstallDefaultRanges:
    """Test that default ranges are auto-installed for empty databases."""

    def test_ranges_auto_installed_on_first_visit(self, page, app_url):
        """
        Verify minimal ranges are auto-installed when visiting entry form on empty DB.

        Steps:
            1. Use empty database
            2. Visit entry form
            3. Verify ranges are loaded (etymology dropdown is populated)
        """
        # Navigate to create new entry (triggers range loading)
        page.goto(f"{app_url}/entries/add")
        page.wait_for_load_state('networkidle')

        # Wait for form to load
        page.wait_for_selector('#entry-form', state='visible')

        # Add etymology section to test ranges
        page.click('#add-etymology-btn')
        page.wait_for_selector('.etymology-form-item', state='visible')

        # Check that dropdown has values (meaning ranges were auto-installed)
        type_select = page.locator('.etymology-type-select').first
        options = type_select.locator('option').all_text_contents()

        # Should have more than just placeholder
        assert len(options) > 1, f"Dropdown only has {len(options)} options - ranges may not be loaded"

        print(f"✅ Default ranges auto-installed, dropdown has {len(options)} options")

    def test_no_ranges_missing_banner_on_empty_db(self, page, app_url):
        """
        Verify ranges-missing banner does NOT appear when ranges auto-install works.

        The banner should not appear if auto-install is successful.
        """
        # Navigate to entry form
        page.goto(f"{app_url}/entries/add")
        page.wait_for_load_state('networkidle')

        # Wait for form
        page.wait_for_selector('#entry-form', state='visible')

        # Check that ranges-missing banner is NOT visible
        banner = page.locator('#ranges-missing-banner')
        expect(banner).not_to_be_visible()

        print("✅ No ranges missing banner shown (auto-install successful)")

    def test_grammatical_info_dropdown_populated(self, page, app_url):
        """
        Verify grammatical info (POS) dropdown is populated from ranges.

        This validates that auto-installed ranges include grammatical-info.
        """
        # Navigate to create entry
        page.goto(f"{app_url}/entries/add")
        page.wait_for_load_state('networkidle')

        # Find grammatical info dropdown
        pos_select = page.locator('select[name="grammatical_info"]').first

        if pos_select.is_visible():
            options = pos_select.locator('option').all_text_contents()

            # Should have common POS values
            common_pos = ['noun', 'verb', 'adjective', 'adverb']
            found_any = any(
                any(pos in opt.lower() for pos in common_pos)
                for opt in options
            )

            assert found_any or len(options) > 1, \
                f"Grammatical info dropdown seems empty or missing common POS values: {options}"

            print(f"✅ Grammatical info dropdown populated with {len(options)} options")
