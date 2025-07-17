"""
Selenium-based UI tests for relations and variants functionality.

These tests use WebDriver to test actual browser interactions with the UI,
ensuring the JavaScript and DOM manipulation work correctly.
"""

from __future__ import annotations

import pytest
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException

from app import create_app
from app.models.entry import Entry
from app.services.dictionary_service import DictionaryService


@pytest.fixture(scope="function")
def chrome_driver():
    """Create a Chrome WebDriver instance for testing."""
    options = Options()
    options.add_argument("--headless")  # Run in headless mode for CI
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--disable-gcm")  # Disable GCM for headless stability
    options.add_argument("--disable-extensions")
    options.add_argument("--disable-background-networking")
    options.add_argument("--disable-notifications")  # Disable notifications
    options.add_argument("--disable-default-apps")   # Disable default apps
    options.add_argument("--disable-component-update")  # Disable component updates


    driver = webdriver.Chrome(options=options)
    driver.implicitly_wait(10)
    yield driver
    driver.quit()


@pytest.fixture(scope="function")
@pytest.mark.integration
def test_app():
    """Create a test Flask app for Selenium testing."""
    app = create_app('testing')
    app.config['TESTING'] = True
    app.config['WTF_CSRF_ENABLED'] = False  # Disable CSRF for testing
    return app


@pytest.fixture(scope="function")
@pytest.mark.integration
def test_entry_with_variants(test_app):
    """Create a test entry with variants for UI testing."""
    with test_app.app_context():
        dict_service = test_app.injector.get(DictionaryService)
        
        # Clean up any existing test entries
        try:
            existing_main = dict_service.get_entry('selenium_test_main')
            if existing_main:
                dict_service.delete_entry('selenium_test_main')
        except:
            pass  # Entry doesn't exist, which is fine
            
        try:
            existing_variant = dict_service.get_entry('selenium_test_variant')
            if existing_variant:
                dict_service.delete_entry('selenium_test_variant')
        except:
            pass  # Entry doesn't exist, which is fine
        
        # Create a main entry
        main_entry = Entry.from_dict({
            'id': 'selenium_test_main',
            'lexical_unit': {'en': 'color'},
            'senses': [{'id': 'sense1', 'glosses': {'en': 'appearance'}}]
        })
        dict_service.create_entry(main_entry)
        
        # Create a variant entry
        variant_entry = Entry.from_dict({
            'id': 'selenium_test_variant',
            'lexical_unit': {'en': 'colour'},
            'senses': [{'id': 'sense1', 'glosses': {'en': 'British spelling'}}],
            'variant_relations': [{
                'type': '_component-lexeme',
                'ref': 'selenium_test_main',
                'variant_type': 'Spelling Variant'
            }]
        })
        dict_service.create_entry(variant_entry)
        
        return main_entry.id, variant_entry.id



@pytest.mark.integration
class TestRelationsVariantsUISelenium:
    """Test relations and variants UI functionality using Selenium WebDriver."""

    @pytest.mark.selenium
    @pytest.mark.integration
    def test_variant_container_displays_correctly(self, chrome_driver, test_app, test_entry_with_variants):
        """Test that the variants container displays without technical debug info."""
        main_id, variant_id = test_entry_with_variants
        
        with test_app.test_request_context():
            # Start the Flask app for Selenium
            import threading
            from werkzeug.serving import make_server
            
            server = make_server('127.0.0.1', 5555, test_app, threaded=True)
            server_thread = threading.Thread(target=server.serve_forever)
            server_thread.daemon = True
            server_thread.start()
            
            try:
                # Navigate to the entry edit page
                chrome_driver.get(f'http://127.0.0.1:5555/entries/{variant_id}/edit')
                
                # Wait for page to load
                wait = WebDriverWait(chrome_driver, 10)
                wait.until(EC.presence_of_element_located((By.ID, "variants-container")))
                
                # Check that variants container exists
                variants_container = chrome_driver.find_element(By.ID, "variants-container")
                assert variants_container.is_displayed()
                
                # Verify that technical debug info is NOT visible to users
                page_source = chrome_driver.page_source
                
                # Get visible text (not including hidden input values)
                visible_text = chrome_driver.find_element(By.TAG_NAME, "body").text
                
                # These should NOT appear in the user-visible text
                assert "_component-lexeme" not in visible_text, "Technical relation type should not be visible to users"
                assert "LIFT format" not in visible_text, "LIFT format references should not be visible to users"
                assert "relation with a variant-type trait" not in visible_text, "Technical trait explanations should not be visible to users"
                
                # The key test is that technical debug info is NOT visible to users
                # Verify that technical debug info is NOT visible to users    
                page_source = chrome_driver.page_source
                
                # Get visible text (not including hidden input values)        
                visible_text = chrome_driver.find_element(By.TAG_NAME, "body").text
                
                # These should NOT appear in the user-visible text
                assert "_component-lexeme" not in visible_text, "Technical relation type should not be visible to users"
                assert "LIFT format" not in visible_text, "LIFT format references should not be visible to users"
                assert "relation with a variant-type trait" not in visible_text, "Technical trait explanations should not be visible to users"
                
                # Check that we have variant items displayed (the main point of the test)
                variant_items = chrome_driver.find_elements(By.CSS_SELECTOR, ".variant-item")
                assert len(variant_items) > 0, "Should have at least one variant item displayed"
                
                # The main success criteria: technical debug info is NOT visible to users (already checked above)
                # And variant relationships are displayed in some user-friendly form (achieved with variant items)
                
                # Check that Order field is not visible to users (if any hidden order inputs exist)
                order_inputs = chrome_driver.find_elements(By.CSS_SELECTOR, "input[name*='[order]']")
                variant_order_inputs = chrome_driver.find_elements(By.CSS_SELECTOR, "input[name*='variant_relations'][name*='[order]']")
                all_order_inputs = order_inputs + variant_order_inputs
                for order_input in all_order_inputs:
                    assert order_input.get_attribute("type") == "hidden", "Order fields should be hidden"
                
            finally:
                server.shutdown()

    @pytest.mark.selenium
    @pytest.mark.integration
    def test_relations_container_displays_correctly(self, chrome_driver, test_app, test_entry_with_variants):
        """Test that the relations container displays without technical debug info."""
        main_id, variant_id = test_entry_with_variants
        
        with test_app.test_request_context():
            # Start the Flask app for Selenium
            import threading
            from werkzeug.serving import make_server
            
            server = make_server('127.0.0.1', 5556, test_app, threaded=True)
            server_thread = threading.Thread(target=server.serve_forever)
            server_thread.daemon = True
            server_thread.start()
            
            try:
                # Navigate to the entry edit page
                chrome_driver.get(f'http://127.0.0.1:5556/entries/{main_id}/edit')
                
                # Wait for page to load
                wait = WebDriverWait(chrome_driver, 10)
                wait.until(EC.presence_of_element_located((By.ID, "relations-container")))
                
                # Check that relations container exists
                relations_container = chrome_driver.find_element(By.ID, "relations-container")
                assert relations_container.is_displayed()
                
                # Verify that technical debug info is NOT visible
                page_source = chrome_driver.page_source
                
                # These should NOT appear in the user-visible UI
                assert "LIFT relation elements" not in page_source
                assert "LIFT format, this creates a relation" not in page_source
                
                # Verify that user-friendly content IS visible
                assert "Relations" in page_source
                assert "Semantic Relationship" in page_source or "No Semantic Relations" in page_source
                
            finally:
                server.shutdown()

    @pytest.mark.selenium
    @pytest.mark.integration
    def test_variant_form_interaction(self, chrome_driver, test_app, test_entry_with_variants):
        """Test adding a new variant through the UI."""
        main_id, variant_id = test_entry_with_variants
        
        with test_app.test_request_context():
            # Start the Flask app for Selenium
            import threading
            from werkzeug.serving import make_server
            
            server = make_server('127.0.0.1', 5557, test_app, threaded=True)
            server_thread = threading.Thread(target=server.serve_forever)
            server_thread.daemon = True
            server_thread.start()
            
            try:
                # Navigate to the entry edit page
                chrome_driver.get(f'http://127.0.0.1:5557/entries/{main_id}/edit')
                
                # Wait for page to load
                wait = WebDriverWait(chrome_driver, 10)
                wait.until(EC.presence_of_element_located((By.ID, "add-variant-btn")))
                
                # Click add variant button
                add_variant_btn = chrome_driver.find_element(By.ID, "add-variant-btn")
                chrome_driver.execute_script("arguments[0].click();", add_variant_btn)
                
                # Wait for new variant form to appear
                time.sleep(1)  # Allow time for DOM manipulation
                
                # Verify that a new variant form appeared
                variant_items = chrome_driver.find_elements(By.CSS_SELECTOR, ".variant-item")
                assert len(variant_items) > 0, "At least one variant form should be present"
                
                # Verify that the form contains user-friendly fields
                variant_type_selects = chrome_driver.find_elements(By.CSS_SELECTOR, "select[name*='variant_type']")
                assert len(variant_type_selects) > 0, "Variant type selector should be present"
                
                # Verify that technical fields are hidden
                hidden_inputs = chrome_driver.find_elements(By.CSS_SELECTOR, "input[type='hidden'][name*='variant_relations']")
                assert len(hidden_inputs) > 0, "Hidden technical fields should be present but not visible"
                
            finally:
                server.shutdown()

    @pytest.mark.selenium 
    @pytest.mark.integration
    def test_relation_form_interaction(self, chrome_driver, test_app, test_entry_with_variants):
        """Test adding a new relation through the UI."""
        main_id, variant_id = test_entry_with_variants
        
        with test_app.test_request_context():
            # Start the Flask app for Selenium
            import threading
            from werkzeug.serving import make_server
            
            server = make_server('127.0.0.1', 5558, test_app, threaded=True)
            server_thread = threading.Thread(target=server.serve_forever)
            server_thread.daemon = True
            server_thread.start()
            
            try:
                # Navigate to the entry edit page
                chrome_driver.get(f'http://127.0.0.1:5558/entries/{main_id}/edit')
                
                # Wait for page to load and JavaScript to initialize
                wait = WebDriverWait(chrome_driver, 10)
                wait.until(EC.presence_of_element_located((By.ID, "add-relation-btn")))
                
                # Wait for JavaScript to be fully loaded and initialized
                wait.until(lambda driver: driver.execute_script("return typeof window.RelationsManager !== 'undefined'"))
                wait.until(lambda driver: driver.execute_script("return typeof window.relationsManager !== 'undefined'"))
                
                # Click add relation button
                add_relation_btn = chrome_driver.find_element(By.ID, "add-relation-btn")
                chrome_driver.execute_script("arguments[0].click();", add_relation_btn)
                
                # Wait for new relation form to appear (increased timeout for reliability)
                wait = WebDriverWait(chrome_driver, 5)
                wait.until(lambda driver: len(driver.find_elements(By.CSS_SELECTOR, ".relation-item")) > 0)
                
                # Verify that a new relation form appeared
                relation_items = chrome_driver.find_elements(By.CSS_SELECTOR, ".relation-item")
                assert len(relation_items) > 0, "At least one relation form should be present"
                
                # Verify that the form contains user-friendly fields
                relation_type_selects = chrome_driver.find_elements(By.CSS_SELECTOR, "select.relation-type-select")
                assert len(relation_type_selects) > 0, "Relation type selector should be present"
                
                # Verify that search functionality is available
                search_inputs = chrome_driver.find_elements(By.CSS_SELECTOR, "input.relation-search-input")
                assert len(search_inputs) > 0, "Relation search input should be present"
                
            finally:
                server.shutdown()
