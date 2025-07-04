"""
Integration test for the complete relations UI with real entry form.

This test loads the actual entry form template and verifies:
1. Relations container properly filters out variant-type relations 
2. JavaScript initialization works correctly
3. LIFT ranges are loaded for relation types
4. No raw IDs are exposed to users
"""

from __future__ import annotations

import os
import tempfile
import pytest
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from app import create_app
from app.models.entry import Entry, Relation


class TestRelationsUIIntegration:
    """Integration test for relations UI with actual entry form."""

    @pytest.fixture(scope="class")
    def app(self):
        """Create test Flask app."""
        app = create_app()
        app.config['TESTING'] = True
        app.config['WTF_CSRF_ENABLED'] = False
        return app

    @pytest.fixture(scope="class")
    def driver(self):
        """Create headless Chrome driver."""
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")
        
        driver = webdriver.Chrome(options=chrome_options)
        driver.implicitly_wait(10)
        yield driver
        driver.quit()

    def test_entry_form_filters_variant_relations_correctly(self, app, driver):
        """Test that the actual entry form template filters out variant-type relations."""
        
        with app.app_context():
            # Create test entry with mixed relation types  
            test_entry = Entry(
                id_="test-main-entry-001",
                lexical_unit={"en": "test word"},
                relations=[
                    # Regular semantic relation (should appear in relations container)
                    Relation(
                        type="synonym",
                        ref="test-synonym-entry-001"
                    ),
                    # Variant-type relation (should appear ONLY in variants container)
                    Relation(
                        type="_component-lexeme",
                        ref="test-variant-entry-001",
                        traits={"variant-type": "Spelling Variant"}
                    ),
                    # Another regular relation
                    Relation(
                        type="antonym", 
                        ref="test-antonym-entry-001"
                    )
                ]
            )
            
            # Mock the entry for template rendering
            with app.test_request_context():
                from flask import render_template
                
                # Render the actual entry form template
                html_content = render_template('entry_form.html', 
                                             entry=test_entry, 
                                             variant_relations=test_entry.variant_relations)
                
                # Write to temporary file
                with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False, encoding='utf-8') as f:
                    f.write(html_content)
                    temp_file = f.name
                
                try:
                    # Load the page in Selenium
                    driver.get(f"file://{os.path.abspath(temp_file)}")
                    
                    # Wait for page to load
                    WebDriverWait(driver, 15).until(
                        EC.presence_of_element_located((By.ID, "relations-container"))
                    )
                    
                    print("\n=== RELATIONS CONTAINER TEST ===")
                    
                    # Check relations container - should contain only non-variant relations
                    relations_container = driver.find_element(By.ID, "relations-container")
                    relation_items = relations_container.find_elements(By.CSS_SELECTOR, ".relation-item")
                    
                    print(f"Found {len(relation_items)} relation items in relations container")
                    
                    # Should have 2 relations (synonym + antonym), NOT 3
                    assert len(relation_items) == 2, f"Expected 2 relations, found {len(relation_items)}"
                    
                    # Verify no variant-type relations are shown
                    relation_texts = []
                    for item in relation_items:
                        # Check the header text to see what type of relation this is
                        try:
                            header = item.find_element(By.CSS_SELECTOR, ".card-header h6")
                            relation_texts.append(header.text.lower())
                        except Exception as e:
                            print(f"Could not get header text: {e}")
                    
                    print(f"Relation headers found: {relation_texts}")
                    
                    # Should not contain any mention of variant or _component-lexeme
                    for text in relation_texts:
                        assert "variant" not in text, f"Found variant in relations container: {text}"
                        assert "_component-lexeme" not in text, f"Found _component-lexeme in relations container: {text}"
                        assert "component-lexeme" not in text, f"Found component-lexeme in relations container: {text}"
                    
                    print("✓ Relations container properly excludes variant-type relations")
                    
                    print("\n=== VARIANTS CONTAINER TEST ===")
                    
                    # Check variants container - should contain the variant-type relation
                    variants_container = driver.find_element(By.ID, "variants-container")
                    variant_items = variants_container.find_elements(By.CSS_SELECTOR, ".variant-item")
                    
                    print(f"Found {len(variant_items)} variant items in variants container")
                    
                    # Should have 1 variant
                    assert len(variant_items) == 1, f"Expected 1 variant, found {len(variant_items)}"
                    
                    # Check that it shows the correct variant type
                    variant_item = variant_items[0]
                    variant_headers = variant_item.find_elements(By.CSS_SELECTOR, ".card-header h6")
                    
                    variant_found = False
                    for header in variant_headers:
                        if "Spelling Variant" in header.text:
                            variant_found = True
                            break
                    
                    assert variant_found, "Could not find 'Spelling Variant' in variants container"
                    print("✓ Variants container properly shows variant-type relations")
                    
                    print("\n=== JAVASCRIPT INITIALIZATION TEST ===")
                    
                    # Wait a bit for JavaScript to initialize
                    driver.implicitly_wait(5)
                    
                    # Check that RelationsManager is available
                    relations_manager_available = driver.execute_script("""
                        return typeof window.RelationsManager !== 'undefined';
                    """)
                    
                    assert relations_manager_available, "RelationsManager class should be available globally"
                    print("✓ RelationsManager JavaScript class is available")
                    
                    # Check if relations dropdowns have the correct range ID
                    relation_selects = relations_container.find_elements(By.CSS_SELECTOR, ".relation-type-select")
                    
                    for select in relation_selects:
                        range_id = select.get_attribute("data-range-id")
                        assert range_id == "lexical-relation", f"Expected range ID 'lexical-relation', got '{range_id}'"
                    
                    print(f"✓ Found {len(relation_selects)} relation selects with correct range ID")
                    
                    print("\n=== SUCCESS: All tests passed! ===")
                    
                finally:
                    # Clean up temp file
                    if os.path.exists(temp_file):
                        os.remove(temp_file)

    def test_no_raw_ids_exposed_in_ui(self, app, driver):
        """Test that no raw IDs are exposed in the relations UI."""
        
        with app.app_context():
            # Create test entry with a relation that has display text
            test_entry = Entry(
                id_="test-main-entry-001",
                lexical_unit={"en": "test word"},
                relations=[
                    # Regular relation with display information
                    Relation(
                        type="synonym",
                        ref="some-long-uuid-that-should-not-be-visible-12345",
                        # In real app, this would be populated by the service
                    ),
                ]
            )
            
            with app.test_request_context():
                from flask import render_template
                
                html_content = render_template('entry_form.html', 
                                             entry=test_entry, 
                                             variant_relations=test_entry.variant_relations)
                
                with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False, encoding='utf-8') as f:
                    f.write(html_content)
                    temp_file = f.name
                
                try:
                    driver.get(f"file://{os.path.abspath(temp_file)}")
                    
                    WebDriverWait(driver, 10).until(
                        EC.presence_of_element_located((By.ID, "relations-container"))
                    )
                    
                    # Check relations container for any visible raw IDs
                    relations_container = driver.find_element(By.ID, "relations-container")
                    
                    # Look for any visible text that looks like a raw ID/UUID
                    page_text = relations_container.text
                    
                    # Check for common ID patterns
                    assert "some-long-uuid-that-should-not-be-visible-12345" not in page_text, \
                        "Raw ID should not be visible in relations container"
                    
                    # Check that search inputs are present (they should be for adding new relations)
                    search_inputs = relations_container.find_elements(By.CSS_SELECTOR, ".relation-search-input")
                    
                    # For existing relations, there should be hidden inputs with the IDs
                    hidden_inputs = relations_container.find_elements(By.CSS_SELECTOR, "input[type='hidden']")
                    
                    print(f"✓ Found {len(search_inputs)} search inputs and {len(hidden_inputs)} hidden inputs")
                    print("✓ No raw IDs exposed in relations UI")
                    
                finally:
                    if os.path.exists(temp_file):
                        os.remove(temp_file)


if __name__ == "__main__":
    # Run the tests
    pytest.main([__file__, "-v"])
