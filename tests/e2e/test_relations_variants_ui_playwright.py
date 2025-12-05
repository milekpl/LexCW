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
def test_entry_with_variants(dict_service_with_db):
    """Create a test entry with variants for UI testing."""
    # Use the dict_service directly (no app context needed for BaseX operations)
    dict_service = dict_service_with_db
    
    # Clean up any existing test entries
    try:
        existing_main = dict_service.get_entry('playwright_test_main')
        if existing_main:
            dict_service.delete_entry('playwright_test_main')
    except Exception:
        pass  # Entry doesn't exist, which is fine
        
    try:
        existing_variant = dict_service.get_entry('playwright_test_variant')
        if existing_variant:
            dict_service.delete_entry('playwright_test_variant')
    except Exception:
        pass  # Entry doesn't exist, which is fine
    
    # Create a main entry
    main_entry = Entry(
        id_='playwright_test_main',
        lexical_unit={'en': 'color'},
        senses=[{'id': 'sense1', 'glosses': {'en': 'appearance'}}]
    )
    dict_service.create_entry(main_entry)
    
    # Create a variant entry
    variant_entry = Entry(
        id_='playwright_test_variant',
        lexical_unit={'en': 'colour'},
        senses=[{'id': 'sense1', 'glosses': {'en': 'British spelling'}}],
        variant_relations=[{
            'type': '_component-lexeme',
            'ref': 'playwright_test_main',
            'variant_type': 'Spelling Variant'
        }]
    )
    dict_service.create_entry(variant_entry)
    
    return main_entry.id, variant_entry.id


@pytest.mark.integration
@pytest.mark.playwright
class TestRelationsVariantsUIPlaywright:
    """Test relations and variants UI functionality using Playwright."""

    def test_variant_container_displays_correctly(self, playwright_page: Page, live_server, test_entry_with_variants):
        """Test that the variants container displays without technical debug info."""
        main_id, variant_id = test_entry_with_variants
        
        # Navigate to the entry edit page
        playwright_page.goto(f'{live_server.url}/entries/{variant_id}/edit')
        
        # Wait for page to load
        playwright_page.wait_for_selector("#variants-container", timeout=10000)
        
        # DEBUG: Take screenshot and check what's visible
        playwright_page.screenshot(path="debug_variant_container.png")
        container_html = playwright_page.locator("#variants-container").inner_html()
        print(f"DEBUG: variants-container HTML length: {len(container_html)}")
        
        # Check that variants container exists and is visible
        variants_container = playwright_page.locator("#variants-container")
        expect(variants_container).to_be_visible()
        
        # Get visible text only (excluding hidden inputs)
        # Use innerText instead of textContent to exclude hidden elements
        visible_text = playwright_page.locator("body").inner_text()
        
        # These should NOT appear in the user-visible text
        assert "_component-lexeme" not in visible_text, "Technical relation type should not be visible to users"
        assert "LIFT format" not in visible_text, "LIFT format references should not be visible to users"
        assert "relation with a variant-type trait" not in visible_text, "Technical trait explanations should not be visible to users"
        
        # Check that we have variant items displayed (the main point of the test)
        variant_items = playwright_page.locator(".variant-item")
        expect(variant_items.first).to_be_visible()
        
        # Check that Order field is not visible to users (if any hidden order inputs exist)
        order_inputs = playwright_page.locator("input[name*='[order]'], input[name*='variant_relations'][name*='[order]']")
        order_count = order_inputs.count()
        
        for i in range(order_count):
            order_input = order_inputs.nth(i)
            assert order_input.get_attribute("type") == "hidden", "Order fields should be hidden"

    def test_relations_container_displays_correctly(self, playwright_page: Page, live_server, test_entry_with_variants):
        """Test that the relations container displays without technical debug info."""
        main_id, variant_id = test_entry_with_variants
        
        # Navigate to the entry edit page
        playwright_page.goto(f'{live_server.url}/entries/{main_id}/edit')
        
        # Wait for page to load
        playwright_page.wait_for_selector("#relations-container", timeout=10000)
        
        # Check that relations container exists and is visible
        relations_container = playwright_page.locator("#relations-container")
        expect(relations_container).to_be_visible()
        
        # Get page source for checking
        page_source = playwright_page.content()
        
        # These should NOT appear in the user-visible UI
        assert "LIFT relation elements" not in page_source
        assert "LIFT format, this creates a relation" not in page_source
        
        # Verify that user-friendly content IS visible
        assert "Relations" in page_source
        assert "Semantic Relationship" in page_source or "No Semantic Relations" in page_source

    def test_variant_form_interaction(self, playwright_page: Page, live_server, test_entry_with_variants):
        """Test adding a new variant through the UI."""
        main_id, variant_id = test_entry_with_variants
        
        # Navigate to the entry edit page
        playwright_page.goto(f'{live_server.url}/entries/{main_id}/edit')
        
        # Wait for page to load
        playwright_page.wait_for_selector("#add-variant-btn", timeout=10000)
        
        # Click add variant button
        add_variant_btn = playwright_page.locator("#add-variant-btn")
        add_variant_btn.click()
        
        # Wait for new variant form to appear
        playwright_page.wait_for_timeout(1000)  # Allow time for DOM manipulation
        
        # Verify that a new variant form appeared
        variant_items = playwright_page.locator(".variant-item")
        expect(variant_items.first).to_be_visible()
        
        # Verify that the form contains user-friendly fields
        variant_type_selects = playwright_page.locator("select[name*='variant_type']")
        expect(variant_type_selects.first).to_be_visible()
        
        # Verify that technical fields are hidden
        hidden_inputs = playwright_page.locator("input[type='hidden'][name*='variant_relations']")
        assert hidden_inputs.count() > 0, "Hidden technical fields should be present but not visible"

    def test_relation_form_interaction(self, playwright_page: Page, live_server, test_entry_with_variants):
        """Test adding a new relation through the UI."""
        main_id, variant_id = test_entry_with_variants
        
        # Navigate to the entry edit page
        playwright_page.goto(f'{live_server.url}/entries/{main_id}/edit')
        
        # Wait for page to load and JavaScript to initialize
        playwright_page.wait_for_selector("#add-relation-btn", timeout=10000)
        
        # Wait for JavaScript to be fully loaded and initialized
        playwright_page.wait_for_function("typeof window.RelationsManager !== 'undefined'")
        playwright_page.wait_for_function("typeof window.relationsManager !== 'undefined'")
        
        # Click add relation button
        add_relation_btn = playwright_page.locator("#add-relation-btn")
        add_relation_btn.click()
        
        # Wait for new relation form to appear (increased timeout for reliability)
        playwright_page.wait_for_selector(".relation-item", timeout=5000)
        
        # Verify that a new relation form appeared
        relation_items = playwright_page.locator(".relation-item")
        expect(relation_items.first).to_be_visible()
        
        # Verify that the form contains user-friendly fields
        relation_type_selects = playwright_page.locator("select.relation-type-select")
        expect(relation_type_selects.first).to_be_visible()
        
        # Verify that search functionality is available
        search_inputs = playwright_page.locator("input.relation-search-input")
        expect(search_inputs.first).to_be_visible()
