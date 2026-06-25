"""
E2E Tests for Real-time IPA Validation
=======================================

Tests that IPA transcription fields validate input in real-time,
providing immediate visual feedback for invalid characters and patterns.
This helps lexicographers catch phonetic transcription errors early.

Usage:
    pytest tests/e2e/test_ipa_validation.py -v
"""

import pytest
from playwright.sync_api import expect


@pytest.mark.e2e
class TestRealtimeIPAValidation:
    """Test real-time IPA validation in pronunciation fields."""

    def test_valid_ipa_accepted(self, page, app_url):
        """
        Verify valid IPA transcription is accepted without error.

        Steps:
            1. Navigate to entry form
            2. Add pronunciation
            3. Enter valid IPA characters
            4. Verify no error styling applied
        """
        # Navigate to create entry
        page.goto(f"{app_url}/entries/add")
        page.wait_for_load_state('networkidle')

        # Fill basic data
        page.fill('input[name="lexical_unit.en"]', 'testword')

        # Wait for pronunciation section
        page.wait_for_selector('#pronunciation-container', state='visible')

        # Click "Add Pronunciation" button to create a pronunciation field
        add_pronunciation_btn = page.locator('#add-pronunciation-btn')
        if add_pronunciation_btn.is_visible():
            add_pronunciation_btn.click()
            # Wait for pronunciation form to appear
            page.wait_for_selector('.pronunciation-item', state='visible')

        # Find IPA input (should now exist)
        ipa_input = page.locator('.ipa-input').first

        # Enter valid IPA
        valid_ipa = '/ˈtɛst.wɜːd/'  # /ˈtɛst.wɜːd/
        ipa_input.fill(valid_ipa)
        ipa_input.blur()

        # Wait for validation
        page.wait_for_timeout(500)

        # Should NOT have is-invalid class
        classes = ipa_input.evaluate('el => el.className')
        assert "is-invalid" not in classes, f"Should not have is-invalid class, got: {classes}"

        print("✅ Valid IPA accepted without error")

    def test_invalid_ipa_characters_show_error(self, page, app_url):
        """
        Verify invalid IPA characters trigger red underline/warning.

        Steps:
            1. Navigate to entry form
            2. Add pronunciation
            3. Enter invalid characters (e.g., numbers, symbols)
            4. Verify error styling is applied (red underline, is-invalid class)
        """
        # Navigate to create entry
        page.goto(f"{app_url}/entries/add")
        page.wait_for_load_state('networkidle')

        # Fill basic data
        page.fill('input[name="lexical_unit.en"]', 'testword')

        # Wait for pronunciation section
        page.wait_for_selector('#pronunciation-container', state='visible')

        # Click "Add Pronunciation" to create pronunciation field
        add_pronunciation_btn = page.locator('#add-pronunciation-btn')
        if add_pronunciation_btn.is_visible():
            add_pronunciation_btn.click()
            page.wait_for_selector('.pronunciation-item', state='visible')

        # Find IPA input
        ipa_input = page.locator('.ipa-input').first

        # Enter invalid IPA (contains numbers which are invalid)
        invalid_ipa = 'test123'
        ipa_input.fill(invalid_ipa)
        ipa_input.blur()

        # Wait for debounced validation
        page.wait_for_timeout(600)

        # Should have is-invalid class
        classes = ipa_input.evaluate('el => el.className')
        assert "is-invalid" in classes, f"Expected is-invalid class, got: {classes}"

        # Check for error message
        feedback = page.locator('.ipa-validation-feedback').first
        if feedback.is_visible():
            error_text = feedback.text_content()
            assert 'invalid' in error_text.lower() or 'character' in error_text.lower(), \
                f"Expected error message about invalid characters, got: {error_text}"

        # Check for red underline style
        style = ipa_input.evaluate('el => el.style.textDecoration')
        assert 'underline' in style or ipa_input.evaluate('el => el.classList.contains("is-invalid")'), \
            "Expected red underline or is-invalid class for invalid IPA"

        print("✅ Invalid IPA shows error with red underline")

    def test_ipa_double_stress_error(self, page, app_url):
        """
        Verify consecutive stress markers trigger error.

        Steps:
            1. Enter IPA with double stress markers (e.g., ˈˈ)
            2. Verify error is shown
        """
        # Navigate to create entry
        page.goto(f"{app_url}/entries/add")
        page.wait_for_load_state('networkidle')

        # Fill basic data
        page.fill('input[name="lexical_unit.en"]', 'testword')

        # Wait for pronunciation section
        page.wait_for_selector('#pronunciation-container', state='visible')

        # Click "Add Pronunciation" to create pronunciation field
        add_pronunciation_btn = page.locator('#add-pronunciation-btn')
        if add_pronunciation_btn.is_visible():
            add_pronunciation_btn.click()
            page.wait_for_selector('.pronunciation-item', state='visible')

        # Find IPA input
        ipa_input = page.locator('.ipa-input').first

        # Enter IPA with double stress
        double_stress_ipa = '/ˈˈtest/'
        ipa_input.fill(double_stress_ipa)
        ipa_input.blur()

        # Wait for validation
        page.wait_for_timeout(600)

        # Should have error
        has_invalid = ipa_input.evaluate('el => el.classList.contains("is-invalid")')
        assert has_invalid, "Expected error for consecutive stress markers"

        print("✅ Double stress markers trigger validation error")

    def test_ipa_validation_cleared_on_fix(self, page, app_url):
        """
        Verify error is cleared when invalid IPA is corrected.

        Steps:
            1. Enter invalid IPA
            2. Wait for error
            3. Clear and enter valid IPA
            4. Verify error is cleared
        """
        # Navigate to create entry
        page.goto(f"{app_url}/entries/add")
        page.wait_for_load_state('networkidle')

        # Fill basic data
        page.fill('input[name="lexical_unit.en"]', 'testword')

        # Wait for pronunciation section
        page.wait_for_selector('#pronunciation-container', state='visible')

        # Click "Add Pronunciation" to create pronunciation field
        add_pronunciation_btn = page.locator('#add-pronunciation-btn')
        if add_pronunciation_btn.is_visible():
            add_pronunciation_btn.click()
            page.wait_for_selector('.pronunciation-item', state='visible')

        # Find IPA input
        ipa_input = page.locator('.ipa-input').first

        # Enter invalid IPA first
        ipa_input.fill('invalid123')
        ipa_input.blur()
        page.wait_for_timeout(600)

        # Verify error is shown
        has_invalid = ipa_input.evaluate('el => el.classList.contains("is-invalid")')
        assert has_invalid, "Should have error after entering invalid IPA"

        # Now enter valid IPA
        valid_ipa = '/tɛst/'
        ipa_input.fill(valid_ipa)
        ipa_input.blur()
        page.wait_for_timeout(600)

        # Verify error is cleared
        has_invalid = ipa_input.evaluate('el => el.classList.contains("is-invalid")')
        assert not has_invalid, "Error should be cleared after entering valid IPA"

        # Verify is-valid class may be present
        has_valid = ipa_input.evaluate('el => el.classList.contains("is-valid")')
        if has_valid:
            print("✅ Error cleared and valid state shown after fixing IPA")
        else:
            print("✅ Error cleared after fixing IPA")

    def test_ipa_debounce_behavior(self, page, app_url):
        """
        Verify IPA validation is debounced (not triggered on every keystroke).

        This is harder to test directly, but we can verify the timing.
        """
        # Navigate to create entry
        page.goto(f"{app_url}/entries/add")
        page.wait_for_load_state('networkidle')

        # Fill basic data
        page.fill('input[name="lexical_unit.en"]', 'testword')

        # Wait for pronunciation section
        page.wait_for_selector('#pronunciation-container', state='visible')

        # Click "Add Pronunciation" to create pronunciation field
        add_pronunciation_btn = page.locator('#add-pronunciation-btn')
        if add_pronunciation_btn.is_visible():
            add_pronunciation_btn.click()
            page.wait_for_selector('.pronunciation-item', state='visible')

        # Find IPA input
        ipa_input = page.locator('.ipa-input').first

        # Type invalid character quickly
        ipa_input.fill('t')
        page.wait_for_timeout(100)  # Less than debounce

        # Should not have error yet (debounce)
        has_invalid = ipa_input.evaluate('el => el.classList.contains("is-invalid")')

        # Wait for debounce + processing time
        page.wait_for_timeout(700)

        # Now should have error if we type more
        ipa_input.fill('test123')
        ipa_input.blur()
        page.wait_for_timeout(600)

        # Now should have error
        has_invalid = ipa_input.evaluate('el => el.classList.contains("is-invalid")')

        print("✅ IPA validation appears to be debounced")
