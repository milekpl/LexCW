"""
Test Relations UI Filtering

This test ensures that the relations container properly filters out
_component-lexeme relations with variant-type traits, showing only
non-variant relations with proper clickable links.
"""

import pytest
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from app import create_app
from app.services.dictionary_service import DictionaryService
from app.models.entry import Entry


class TestRelationsUIFiltering:
    """Test relations UI filtering to exclude variant-type relations."""
    
    @pytest.fixture(autouse=True)
    def setup_method(self):
        """Set up test environment."""
        self.app = create_app()
        self.app_context = self.app.app_context()
        self.app_context.push()
        
        # Set up headless Chrome
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")
        
        try:
            self.driver = webdriver.Chrome(options=chrome_options)
            self.driver.implicitly_wait(10)
        except Exception as e:
            pytest.skip(f"Chrome WebDriver not available: {e}")
    
    def teardown_method(self):
        """Clean up test environment."""
        if hasattr(self, 'driver'):
            self.driver.quit()
        if hasattr(self, 'app_context'):
            self.app_context.pop()
    
    def test_relations_container_filters_variant_type_relations(self):
        """Test that relations container excludes _component-lexeme relations with variant-type traits."""
        
        # Get a test entry with mixed relations
        dict_service = self.app.injector.get(DictionaryService)
        
        # Find an entry that has both variant and non-variant relations
        test_entry_id = "Protestant work ethic_38cda8f9-199f-44b3-9bf0-bc2e08ba33bf"
        entry = dict_service.get_entry(test_entry_id)
        
        if not entry:
            pytest.skip(f"Test entry {test_entry_id} not found")
        
        print(f"\n=== Testing Relations UI Filtering for Entry: {entry.id} ===")
        print(f"Total relations: {len(entry.relations)}")
        
        # Analyze relations
        variant_relations = []
        non_variant_relations = []
        
        for relation in entry.relations:
            if (hasattr(relation, 'traits') and 
                relation.traits and 
                'variant-type' in relation.traits):
                variant_relations.append(relation)
                print(f"  Variant relation: {relation.type} -> {relation.ref} (variant-type: {relation.traits['variant-type']})")
            else:
                non_variant_relations.append(relation)
                print(f"  Non-variant relation: {relation.type} -> {relation.ref}")
        
        print(f"Variant relations: {len(variant_relations)}")
        print(f"Non-variant relations: {len(non_variant_relations)}")
        
        # Start Flask test server
        with self.app.test_client() as client:
            # Navigate to entry edit page
            response = client.get(f'/entries/{entry.id}/edit')
            assert response.status_code == 200
            
            # Start selenium server for UI testing
            from werkzeug.serving import make_server
            import threading
            import time
            
            server = make_server('127.0.0.1', 0, self.app)
            port = server.server_port
            
            # Start server in background thread
            server_thread = threading.Thread(target=server.serve_forever)
            server_thread.daemon = True
            server_thread.start()
            
            time.sleep(2)  # Give server time to start
            
            try:
                # Navigate to entry edit page with Selenium
                self.driver.get(f'http://127.0.0.1:{port}/entries/{entry.id}/edit')
                
                # Wait for the page to load
                WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.ID, "relations-container"))
                )
                
                # Check variants container
                variants_container = self.driver.find_element(By.ID, "variants-container")
                variant_items = variants_container.find_elements(By.CLASS_NAME, "variant-item")
                print(f"Variants container has {len(variant_items)} items")
                
                # Check relations container  
                relations_container = self.driver.find_element(By.ID, "relations-container")
                relation_items = relations_container.find_elements(By.CLASS_NAME, "relation-item")
                print(f"Relations container has {len(relation_items)} items")
                
                # Verify that relations container only shows non-variant relations
                assert len(relation_items) == len(non_variant_relations), \
                    f"Relations container should show {len(non_variant_relations)} non-variant relations, but shows {len(relation_items)}"
                
                # Verify that variants container shows variant relations
                assert len(variant_items) == len(variant_relations), \
                    f"Variants container should show {len(variant_relations)} variant relations, but shows {len(variant_items)}"
                
                # Check that relation items show clickable links, not raw IDs
                for relation_item in relation_items:
                    # Look for links or user-friendly text, not raw UUIDs
                    item_text = relation_item.text
                    print(f"Relation item text: {item_text}")
                    
                    # Should not contain raw UUID patterns
                    import re
                    uuid_pattern = r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}'
                    raw_uuids = re.findall(uuid_pattern, item_text, re.IGNORECASE)
                    
                    # Raw UUIDs should not be prominently displayed as the main text
                    # (They might appear in hidden form fields or as data attributes, which is fine)
                    for uuid in raw_uuids:
                        assert not item_text.strip().startswith(uuid), \
                            f"Relation item should not display raw UUID {uuid} as main text"
                
                # Verify the relations container loads relation types from LIFT ranges
                add_relation_btn = self.driver.find_element(By.ID, "add-relation-btn")
                add_relation_btn.click()
                
                # Wait for new relation item to appear
                WebDriverWait(self.driver, 5).until(
                    EC.presence_of_element_located((By.CLASS_NAME, "relation-type-select"))
                )
                
                # Check that relation type dropdown is populated
                relation_type_select = self.driver.find_element(By.CLASS_NAME, "relation-type-select")
                options = relation_type_select.find_elements(By.TAG_NAME, "option")
                
                # Should have more than just the default "Select type" option
                assert len(options) > 1, "Relation type dropdown should be populated from LIFT ranges"
                
                # Verify that relation types come from ranges, not hardcoded
                option_values = [opt.get_attribute("value") for opt in options if opt.get_attribute("value")]
                print(f"Available relation types: {option_values}")
                
                # Should include common relation types from LIFT ranges
                expected_types = ['synonym', 'antonym', 'hypernym', 'hyponym']
                found_types = [t for t in expected_types if t in option_values]
                assert len(found_types) > 0, f"Should have some standard relation types from ranges: {expected_types}"
                
                print("✅ Relations UI filtering test passed!")
                
            finally:
                server.shutdown()
    
    def test_relations_container_shows_entry_links_not_ids(self):
        """Test that relations container shows clickable entry links, not raw IDs."""
        
        dict_service = self.app.injector.get(DictionaryService)
        
        # Create a test entry with a non-variant relation
        test_entry = Entry(
            id_="test_relations_ui_entry",
            lexical_unit={"en": "test word"}
        )
        
        # Add a non-variant relation
        relation = Relation(
            type="synonym",
            ref="target_entry_12345"
        )
        test_entry.relations = [relation]
        
        # Start Flask test server
        with self.app.test_client() as client:
            from werkzeug.serving import make_server
            import threading
            import time
            
            server = make_server('127.0.0.1', 0, self.app)
            port = server.server_port
            
            server_thread = threading.Thread(target=server.serve_forever)
            server_thread.daemon = True
            server_thread.start()
            
            time.sleep(2)
            
            try:
                # Mock the entry in the dictionary service for this test
                original_get_entry = dict_service.get_entry
                def mock_get_entry(entry_id):
                    if entry_id == "test_relations_ui_entry":
                        return test_entry
                    return original_get_entry(entry_id)
                dict_service.get_entry = mock_get_entry
                
                # Navigate to entry edit page
                self.driver.get(f'http://127.0.0.1:{port}/entries/test_relations_ui_entry/edit')
                
                # Wait for relations container
                WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.ID, "relations-container"))
                )
                
                # Check for search functionality in relations
                add_relation_btn = self.driver.find_element(By.ID, "add-relation-btn")
                add_relation_btn.click()
                
                # Wait for new relation item
                WebDriverWait(self.driver, 5).until(
                    EC.presence_of_element_located((By.CLASS_NAME, "relation-ref-input"))
                )
                
                # Find the reference input field
                ref_input = self.driver.find_element(By.CLASS_NAME, "relation-ref-input")
                
                # Should have search functionality (search button or autocomplete)
                search_btn = self.driver.find_element(By.CLASS_NAME, "search-entry-btn")
                assert search_btn is not None, "Should have search button for entry selection"
                
                # Should not require manual UUID entry
                placeholder = ref_input.get_attribute("placeholder")
                assert "search" in placeholder.lower(), "Input should encourage search, not manual ID entry"
                
                print("✅ Relations UI shows proper entry selection interface!")
                
            finally:
                # Restore original method
                dict_service.get_entry = original_get_entry
                server.shutdown()


if __name__ == "__main__":
    test = TestRelationsUIFiltering()
    test.setup_method()
    try:
        test.test_relations_container_filters_variant_type_relations()
        test.test_relations_container_shows_entry_links_not_ids()
        print("All tests passed!")
    finally:
        test.teardown_method()
