"""
Playwright-based UI tests for relations and variants functionality.

These tests use Playwright to test actual browser interactions with the UI,
ensuring the JavaScript and DOM manipulation work correctly.

Ported from Selenium to Playwright to use modern testing infrastructure.
"""

from __future__ import annotations

import pytest
from playwright.sync_api import Page, expect

from app.models.entry import Entry


@pytest.fixture(scope="function")
def test_entry_with_variants(app_url: str, configured_flask_app):
    """Create a test entry with variants for UI testing using the API.

    Ensures entries are created in the current test database context.
    Returns (main_entry_id, variant_entry_id).
    """
    import requests
    app, _ = configured_flask_app
    base_url = app_url

    # Create main entry
    main_entry = {
        "id": "playwright_test_main",
        "lexical_unit": {"en": "color"},
        "senses": [{"id": "sense1", "gloss": {"en": "appearance"}}]
    }
    r = requests.post(f"{base_url}/api/entries/", json=main_entry, headers={"Content-Type": "application/json"})
    if r.status_code not in (200, 201):
        raise RuntimeError(f"Failed to create main test entry: {r.status_code} {r.text}")

    # Create variant entry referencing main
    variant_entry = {
        "id": "playwright_test_variant",
        "lexical_unit": {"en": "colour"},
        "senses": [{"id": "sense1", "gloss": {"en": "British spelling"}}],
        "variant_relations": [{
            "type": "_component-lexeme",
            "ref": "playwright_test_main",
            "variant_type": "Spelling Variant"
        }]
    }
    r2 = requests.post(f"{base_url}/api/entries/", json=variant_entry, headers={"Content-Type": "application/json"})
    if r2.status_code not in (200, 201):
        raise RuntimeError(f"Failed to create variant test entry: {r2.status_code} {r2.text}")

    return main_entry["id"], variant_entry["id"]


@pytest.mark.integration
@pytest.mark.playwright
class TestRelationsVariantsUIPlaywright:
    """Test relations and variants UI functionality using Playwright."""

    def test_variant_container_displays_correctly(self, page: Page, app_url, test_entry_with_variants):
        """Test that the variants container displays without technical debug info."""
        main_id, variant_id = test_entry_with_variants
        
        # Navigate to the entry edit page
        page.goto(f'{app_url}/entries/{variant_id}/edit')
        
        # Wait for page to load
        page.wait_for_selector("#variants-container", timeout=10000)
        
        # DEBUG: Take screenshot and check what's visible
        page.screenshot(path="debug_variant_container.png")
        container_html = page.locator("#variants-container").inner_html()
        print(f"DEBUG: variants-container HTML length: {len(container_html)}")
        
        # Check that variants container exists and is visible
        variants_container = page.locator("#variants-container")
        expect(variants_container).to_be_visible()
        
        # Get visible text only (excluding hidden inputs)
        # Use innerText instead of textContent to exclude hidden elements
        visible_text = page.locator("body").inner_text()
        
        # These should NOT appear in the user-visible text
        assert "_component-lexeme" not in visible_text, "Technical relation type should not be visible to users"
        assert "LIFT format" not in visible_text, "LIFT format references should not be visible to users"
        assert "relation with a variant-type trait" not in visible_text, "Technical trait explanations should not be visible to users"
        
        # Check that we have variant items displayed (the main point of the test)
        variant_items = page.locator(".variant-item")
        expect(variant_items.first).to_be_visible()
        
        # Check that Order field is not visible to users (if any hidden order inputs exist)
        order_inputs = page.locator("input[name*='[order]'], input[name*='variant_relations'][name*='[order]']")
        order_count = order_inputs.count()
        
        for i in range(order_count):
            order_input = order_inputs.nth(i)
            assert order_input.get_attribute("type") == "hidden", "Order fields should be hidden"

    def test_relations_container_displays_correctly(self, page: Page, app_url, test_entry_with_variants):
        """Test that the relations container displays without technical debug info."""
        main_id, variant_id = test_entry_with_variants
        
        # Navigate to the entry edit page
        page.goto(f'{app_url}/entries/{main_id}/edit')
        
        # Wait for page to load
        page.wait_for_selector("#relations-container", timeout=10000)
        
        # Check that relations container exists and is visible
        relations_container = page.locator("#relations-container")
        expect(relations_container).to_be_visible()
        
        # Get page source for checking
        page_source = page.content()
        
        # These should NOT appear in the user-visible UI
        assert "LIFT relation elements" not in page_source
        assert "LIFT format, this creates a relation" not in page_source
        
        # Verify that user-friendly content IS visible
        assert "Relations" in page_source
        assert "Semantic Relationship" in page_source or "No Semantic Relations" in page_source

    def test_variant_form_interaction(self, page: Page, app_url, test_entry_with_variants):
        """Test adding a new variant through the UI."""
        main_id, variant_id = test_entry_with_variants
        
        # Navigate to the entry edit page
        page.goto(f'{app_url}/entries/{main_id}/edit')
        
        # Wait for page to load
        page.wait_for_selector("#add-variant-btn", timeout=10000)
        
        # Click add variant button
        add_variant_btn = page.locator("#add-variant-btn")
        add_variant_btn.click()
        
        # Wait for new variant form to appear
        page.wait_for_timeout(1000)  # Allow time for DOM manipulation
        
        # Verify that a new variant form appeared
        variant_items = page.locator(".variant-item")
        expect(variant_items.first).to_be_visible()
        
        # Verify that the form contains user-friendly fields
        variant_type_selects = page.locator("select[name*='variant_type']")
        expect(variant_type_selects.first).to_be_visible()
        
        # Verify that technical fields are hidden
        hidden_inputs = page.locator("input[type='hidden'][name*='variant_relations']")
        assert hidden_inputs.count() > 0, "Hidden technical fields should be present but not visible"

    def test_relation_form_interaction(self, page: Page, app_url, test_entry_with_variants):
        """Test adding a new relation through the UI."""
        main_id, variant_id = test_entry_with_variants
        
        # Navigate to the entry edit page
        page.goto(f'{app_url}/entries/{main_id}/edit')
        
        # Wait for page to load and JavaScript to initialize
        page.wait_for_selector("#add-relation-btn", timeout=10000)
        
        # Wait for JavaScript to be fully loaded and initialized
        page.wait_for_function("typeof window.RelationsManager !== 'undefined'")
        page.wait_for_function("typeof window.relationsManager !== 'undefined'")
        
        # Click add relation button
        add_relation_btn = page.locator("#add-relation-btn")
        add_relation_btn.click()
        
        # Wait for new relation form to appear (increased timeout for reliability)
        page.wait_for_selector(".relation-item", timeout=5000)
        
        # Verify that a new relation form appeared
        relation_items = page.locator(".relation-item")
        expect(relation_items.first).to_be_visible()
        
        # Verify that the form contains user-friendly fields
        relation_type_selects = page.locator("select.lexical-relation-select")
        expect(relation_type_selects.first).to_be_visible()
        
        # Verify that search functionality is available
        search_inputs = page.locator("input.relation-search-input")
        expect(search_inputs.first).to_be_visible()
