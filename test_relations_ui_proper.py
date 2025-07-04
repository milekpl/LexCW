"""
Test for proper relations UI behavior.

This test ensures that:
1. Relations container shows only non-variant relations (excludes _component-lexeme with variant-type)
2. Relations are displayed as clickable links, NOT raw IDs
3. Variant-type relations appear only in variants container
4. Relations container properly loads relation types from LIFT ranges
"""

from __future__ import annotations

import os
import pytest
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException

from app import create_app
from app.models.entry import Entry, Relation
from app.services.dictionary_service import DictionaryService
from app.database.mock_connector import MockDatabaseConnector


class TestRelationsUI:
    """Test relations UI filtering and display behavior."""

    @pytest.fixture(scope="class")
    def app(self):
        """Create test Flask app."""
        app = create_app()
        app.config['TESTING'] = True
        app.config['WTF_CSRF_ENABLED'] = False
        return app

    @pytest.fixture(scope="class")
    def client(self, app):
        """Create test client."""
        return app.test_client()

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

    @pytest.fixture
    def test_entries(self, app):
        """Create test entries with various relation types."""
        with app.app_context():
            # Create mock connector for testing
            mock_connector = MockDatabaseConnector()
            dict_service = DictionaryService(mock_connector)
            
            # Create main entry
            main_entry = Entry(
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
            
            # Create related entries for display
            synonym_entry = Entry(
                id_="test-synonym-entry-001",
                lexical_unit={"en": "synonym word"}
            )
            
            variant_entry = Entry(
                id_="test-variant-entry-001", 
                lexical_unit={"en": "variant spelling"}
            )
            
            antonym_entry = Entry(
                id_="test-antonym-entry-001",
                lexical_unit={"en": "opposite word"}
            )
            
            # Save all entries
            dict_service.save_entry(main_entry)
            dict_service.save_entry(synonym_entry)
            dict_service.save_entry(variant_entry)
            dict_service.save_entry(antonym_entry)
            
            return {
                'main': main_entry,
                'synonym': synonym_entry,
                'variant': variant_entry,
                'antonym': antonym_entry
            }

    def test_relations_container_excludes_variant_type_relations(self, app, client, driver, test_entries):
        """Test that relations container excludes _component-lexeme relations with variant-type traits."""
        
        with app.app_context():
            # Navigate to the entry form
            main_entry = test_entries['main']
            response = client.get(f'/entries/{main_entry.id}/edit')
            assert response.status_code == 200
            
            # Save the HTML to a temporary file for Selenium
            temp_file = "temp_entry_form.html"
            with open(temp_file, 'w', encoding='utf-8') as f:
                f.write(response.get_data(as_text=True))
            
            try:
                # Load the page in Selenium
                driver.get(f"file://{os.path.abspath(temp_file)}")
                
                # Wait for page to load
                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.ID, "relations-container"))
                )
                
                # Check relations container - should contain only non-variant relations
                relations_container = driver.find_element(By.ID, "relations-container")
                
                # Should find synonym and antonym relations but NOT variant relation
                relation_items = relations_container.find_elements(By.CSS_SELECTOR, ".relation-item")
                
                # Should have 2 relations (synonym + antonym), NOT 3
                assert len(relation_items) == 2, f"Expected 2 relations, found {len(relation_items)}"
                
                # Verify the relation types displayed
                displayed_types = []
                for item in relation_items:
                    try:
                        type_select = item.find_element(By.CSS_SELECTOR, ".relation-type-select")
                        selected_option = type_select.find_element(By.CSS_SELECTOR, "option[selected]")
                        displayed_types.append(selected_option.get_attribute("value"))
                    except NoSuchElementException:
                        # Check header text as fallback
                        header = item.find_element(By.CSS_SELECTOR, ".card-header h6")
                        header_text = header.text
                        if "synonym" in header_text.lower():
                            displayed_types.append("synonym")
                        elif "antonym" in header_text.lower():
                            displayed_types.append("antonym")
                
                # Should contain synonym and antonym but NOT _component-lexeme
                assert "synonym" in displayed_types, "Synonym relation should be displayed"
                assert "antonym" in displayed_types, "Antonym relation should be displayed"
                assert "_component-lexeme" not in displayed_types, "Variant-type relation should NOT be in relations container"
                
            finally:
                # Clean up temp file
                if os.path.exists(temp_file):
                    os.remove(temp_file)

    def test_variants_container_shows_only_variant_type_relations(self, app, client, driver, test_entries):
        """Test that variants container shows only _component-lexeme relations with variant-type traits."""
        
        with app.app_context():
            main_entry = test_entries['main']
            response = client.get(f'/entries/{main_entry.id}/edit')
            assert response.status_code == 200
            
            temp_file = "temp_entry_form_variants.html"
            with open(temp_file, 'w', encoding='utf-8') as f:
                f.write(response.get_data(as_text=True))
            
            try:
                driver.get(f"file://{os.path.abspath(temp_file)}")
                
                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.ID, "variants-container"))
                )
                
                # Check variants container - should contain only variant-type relations
                variants_container = driver.find_element(By.ID, "variants-container")
                
                # Should find the variant relation
                variant_items = variants_container.find_elements(By.CSS_SELECTOR, ".variant-item")
                
                # Should have 1 variant
                assert len(variant_items) == 1, f"Expected 1 variant, found {len(variant_items)}"
                
                # Verify it's the correct variant
                variant_item = variant_items[0]
                header = variant_item.find_element(By.CSS_SELECTOR, ".card-header h6")
                assert "Spelling Variant" in header.text, "Should show variant type in header"
                
            finally:
                if os.path.exists(temp_file):
                    os.remove(temp_file)

    def test_relations_display_clickable_links_not_raw_ids(self, app, client, driver, test_entries):
        """Test that relations are displayed as clickable links, not raw IDs."""
        
        with app.app_context():
            main_entry = test_entries['main']
            response = client.get(f'/entries/{main_entry.id}/edit')
            assert response.status_code == 200
            
            temp_file = "temp_entry_form_links.html"
            with open(temp_file, 'w', encoding='utf-8') as f:
                f.write(response.get_data(as_text=True))
            
            try:
                driver.get(f"file://{os.path.abspath(temp_file)}")
                
                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.ID, "relations-container"))
                )
                
                relations_container = driver.find_element(By.ID, "relations-container")
                relation_items = relations_container.find_elements(By.CSS_SELECTOR, ".relation-item")
                
                for item in relation_items:
                    # Look for clickable links (not input fields with raw IDs)
                    links = item.find_elements(By.CSS_SELECTOR, "a[href*='/entries/']")
                    
                    # Should have at least one clickable link to the target entry
                    assert len(links) >= 1, "Relation should display as clickable link"
                    
                    # The link text should be human-readable, not a raw ID
                    for link in links:
                        link_text = link.text.strip()
                        assert link_text, "Link should have visible text"
                        # Should not be a GUID or UUID pattern
                        assert not link_text.count('-') >= 4, f"Link text '{link_text}' looks like a raw ID"
                        assert len(link_text) < 50, f"Link text '{link_text}' is too long to be user-friendly"
                
            finally:
                if os.path.exists(temp_file):
                    os.remove(temp_file)

    def test_relations_load_types_from_lift_ranges(self, app, client, driver, test_entries):
        """Test that relation types are loaded from LIFT ranges, not hardcoded."""
        
        with app.app_context():
            main_entry = test_entries['main']
            response = client.get(f'/entries/{main_entry.id}/edit')
            assert response.status_code == 200
            
            temp_file = "temp_entry_form_ranges.html"
            with open(temp_file, 'w', encoding='utf-8') as f:
                f.write(response.get_data(as_text=True))
            
            try:
                driver.get(f"file://{os.path.abspath(temp_file)}")
                
                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.ID, "relations-container"))
                )
                
                # Wait for JavaScript to load ranges
                WebDriverWait(driver, 15).until(
                    lambda d: d.execute_script("""
                        const selects = document.querySelectorAll('.relation-type-select');
                        return Array.from(selects).some(select => select.options.length > 1);
                    """)
                )
                
                # Check that relation type dropdowns are populated from ranges
                relation_selects = driver.find_elements(By.CSS_SELECTOR, ".relation-type-select")
                
                for select in relation_selects:
                    # Should have data-range-id attribute pointing to lexical-relation range
                    range_id = select.get_attribute("data-range-id")
                    assert range_id == "lexical-relation", f"Expected range ID 'lexical-relation', got '{range_id}'"
                    
                    # Should have options loaded from the range (more than just the default option)
                    options = select.find_elements(By.TAG_NAME, "option")
                    assert len(options) > 1, "Relation type dropdown should be populated from LIFT ranges"
                    
                    # Check that options include expected relation types
                    option_values = [opt.get_attribute("value") for opt in options if opt.get_attribute("value")]
                    
                    # Should include common semantic relation types
                    expected_types = ["synonym", "antonym", "hypernym", "hyponym"]
                    found_types = [t for t in expected_types if t in option_values]
                    assert len(found_types) >= 2, f"Should find standard relation types, got: {option_values}"
                
            finally:
                if os.path.exists(temp_file):
                    os.remove(temp_file)


if __name__ == "__main__":
    # Run the tests
    pytest.main([__file__, "-v"])
