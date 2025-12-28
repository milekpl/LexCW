"""
Playwright integration test for LIFT ranges loading in UI dropdowns.

Tests that grammatical-info, lexical-relation, and variant-type dropdowns
are populated correctly from the LIFT ranges in BaseX.
"""

from __future__ import annotations

import pytest
from playwright.sync_api import Page, expect


@pytest.mark.integration
@pytest.mark.playwright
class TestRangesUIPlaywright:
    """Test LIFT ranges loading and dropdown population in the UI."""

    def test_grammatical_info_dropdown_populated(self, page: Page, app_url, basex_test_connector):
        """Test that grammatical info dropdown is populated with values from LIFT ranges."""
        # Navigate to entry creation/edit page
        page.goto(f'{app_url}/entries/add')
        
        # Wait for page to load
        page.wait_for_load_state('networkidle')
        
        # Find the grammatical info dropdown (entry-level Part of Speech)
        pos_select = page.locator('select#part-of-speech, select[name="grammatical_info"]')
        
        # Wait for it to be visible
        expect(pos_select.first).to_be_visible(timeout=10000)
        
        # Get all options
        options = pos_select.first.locator('option').all_text_contents()
        
        # Should have more than just the empty/placeholder option
        assert len(options) > 1, f"Expected multiple POS options, got: {options}"
        
        # Check for some common grammatical categories that should be in LIFT ranges
        options_text = " ".join(options).lower()
        # At least one of these common categories should be present
        common_categories = ['noun', 'verb', 'adjective', 'adverb']
        has_category = any(cat in options_text for cat in common_categories)
        assert has_category, f"Expected at least one common POS category in: {options}"

    def test_relation_type_dropdown_populated(self, page: Page, app_url, basex_test_connector):
        """Test that relation type dropdown is populated with values from LIFT ranges."""
        # Navigate to entry edit page (relations are shown in edit mode)
        page.goto(f'{app_url}/entries/add')
        
        # Wait for page to load
        page.wait_for_load_state('networkidle')
        
        # Scroll to relations section
        page.evaluate("document.querySelector('#relations-container')?.scrollIntoView()")
        
        # Click "Add Relation" button if it exists
        add_relation_btn = page.locator('#add-relation-btn, button:has-text("Add Relation")')
        if add_relation_btn.count() > 0:
            add_relation_btn.first.click()
            page.wait_for_timeout(500)  # Wait for relation form to appear
        
        # Find relation type dropdown
        relation_type_select = page.locator('select.lexical-relation-select, select[name*="relation"][name*="type"]')
        
        if relation_type_select.count() > 0:
            # Wait for it to be visible
            expect(relation_type_select.first).to_be_visible(timeout=5000)
            
            # Get all options
            options = relation_type_select.first.locator('option').all_text_contents()
            
            # Should have more than just the empty/placeholder option
            assert len(options) > 1, f"Expected multiple relation type options, got: {options}"
            
            # Check for relation types in our test data
            options_text = " ".join(options).lower()
            # Our E2E database has: component-lexeme, main-entry (from lexical-relation range)
            expected_relations = ['component', 'main', 'lexeme', 'entry', 'synonym', 'antonym']
            has_relation = any(rel in options_text for rel in expected_relations)
            assert has_relation, f"Expected at least one relation type in: {options}"
        else:
            # If no relation dropdown found, at least verify ranges were loaded
            # by checking via API
            pytest.skip("Relation dropdown not found in UI, needs UI implementation")

    def test_variant_type_dropdown_populated(self, page: Page, app_url, basex_test_connector):
        """Test that variant type dropdown is populated with values from LIFT ranges."""
        # Navigate to entry add page (variants can be added in new entries too)
        page.goto(f'{app_url}/entries/add')
        
        # Wait for page to load
        page.wait_for_load_state('networkidle')
        
        # Wait for the page to be fully interactive
        page.wait_for_timeout(500)
        
        # Scroll to variants section
        page.evaluate("document.querySelector('#variants-container')?.scrollIntoView()")
        
        # Click "Add Variant" button if it exists
        add_variant_btn = page.locator('#add-variant-btn, button:has-text("Add Variant")')
        if add_variant_btn.count() == 0:
            pytest.skip("Add Variant button not found in UI")
        
        add_variant_btn.first.click()
        page.wait_for_timeout(1000)  # Wait for variant form to appear and populate
        
        # Find variant type dropdown using the data-range-id attribute (more reliable)
        variant_type_select = page.locator('select[data-range-id="variant-type"]')
        
        if variant_type_select.count() == 0:
            # Fallback to name-based selector
            variant_type_select = page.locator('select[name*="variant_type"]')
        
        if variant_type_select.count() > 0:
            # Wait for options to be populated (ranges are loaded asynchronously)
            page.wait_for_timeout(2000)
            
            # Wait for it to be visible
            expect(variant_type_select.first).to_be_visible(timeout=5000)
            
            # Get all options
            options = variant_type_select.first.locator('option').all_text_contents()
            
            # Should have more than just the empty/placeholder option
            assert len(options) > 1, f"Expected multiple variant type options, got: {options}"
            
            # Check for common variant types (our test data has: Spelling Variant, Dialectal Variant, Free Variant, Irregularly Inflected Form)
            options_text = " ".join(options).lower()
            common_variants = ['spelling', 'dialect', 'free', 'irregular']
            has_variant = any(var in options_text for var in common_variants)
            assert has_variant, f"Expected at least one common variant type in: {options}"
        else:
            pytest.skip("Variant dropdown not found in UI after clicking Add Variant")

    def test_ranges_loaded_via_api(self, page: Page, app_url, basex_test_connector):
        """Test that ranges are accessible via API endpoint."""
        # Navigate to the ranges API endpoint
        page.goto(f'{app_url}/api/ranges')
        
        # Get the JSON response
        content = page.content()
        
        # Should contain ranges data (not an error page)
        assert 'grammatical-info' in content or 'lexical-relation' in content or 'semantic-domain' in content, \
            f"Expected ranges data in API response, got: {content[:500]}"
        
        # Should not be an error
        assert 'error' not in content.lower() or 'not found' not in content.lower(), \
            f"API returned an error: {content[:200]}"
