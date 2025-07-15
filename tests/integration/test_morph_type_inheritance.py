#!/usr/bin/env python3
"""
Test morph-type respect for existing LIFT data
"""

from __future__ import annotations
import os
import pytest
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
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

@pytest.mark.integration
class TestMorphTypeInheritance:
    """Test that morph-type respects existing LIFT data and doesn't auto-override"""
    
    @pytest.mark.selenium
    @pytest.mark.integration
    def test_existing_morph_type_not_overridden(self, chrome_driver, test_app, dict_service_with_db: DictionaryService, flask_test_server):
        """Test that entries with existing morph-type in LIFT aren't overridden"""
        # Clean up any existing test entries
        try:
            existing = dict_service_with_db.get_entry('test-morph-123')
            if existing:
                dict_service_with_db.delete_entry('test-morph-123')
        except Exception:
            pass  # Entry doesn't exist, which is fine
        
        # Create an entry with existing morph-type "stem" (from LIFT)
        entry_data = {
            'id_': 'test-morph-123',
            'lexical_unit': {'en': 'Protestant'},
            'morph_type': 'stem',  # Existing from LIFT data
            'senses': [{'id': 'sense1', 'glosses': {'en': 'test definition'}}]
        }
        
        entry = Entry.from_dict(entry_data)
        print(f"Created entry with ID: {entry.id}")
        
        # Try to create the entry and check if it was successful
        try:
            created_id = dict_service_with_db.create_entry(entry)
            print(f"Entry created with ID: {created_id}")
            
            # Verify the entry was actually created
            retrieved_entry = dict_service_with_db.get_entry(created_id)
            print(f"Retrieved entry: {retrieved_entry.id if retrieved_entry else 'None'}")
            
        except Exception as e:
            print(f"Error creating entry: {e}")
            import traceback
            traceback.print_exc()
            raise
            
        entry_id = entry.id
        
        wait = WebDriverWait(chrome_driver, 10)
        
        # Debug: Print the database name being used
        print(f"Test database name: {dict_service_with_db.db_connector.database}")
        
        # Navigate to edit form
        edit_url = f'{flask_test_server}/entries/{entry_id}/edit'
        print(f"Navigating to: {edit_url}")
        
        # First try to visit the home page to verify the Flask app is working
        print("Testing Flask app connection...")
        chrome_driver.get(flask_test_server)
        print(f"Home page title: {chrome_driver.title}")
        print(f"Home page URL: {chrome_driver.current_url}")
        
        # Now try the edit URL
        chrome_driver.get(edit_url)
        
        # Debug: Print the page title and current URL
        print(f"Page title: {chrome_driver.title}")
        print(f"Current URL: {chrome_driver.current_url}")
        
        # Debug: Check if we got an error page
        if "error" in chrome_driver.title.lower() or "404" in chrome_driver.title.lower():
            print("ERROR PAGE DETECTED!")
            print("Page source:")
            print(chrome_driver.page_source[:1000])  # First 1000 chars
        
        # Wait for page to load and ranges to be populated
        try:
            wait.until(EC.presence_of_element_located((By.ID, 'lexical-unit')))
            print("Found lexical-unit element")
        except Exception as e:
            print(f"Failed to find lexical-unit element: {e}")
            # Print some page info to debug
            print(f"Page source length: {len(chrome_driver.page_source)}")
            print("Page source preview:")
            print(chrome_driver.page_source[:2000])  # First 2000 chars
            raise
            
        time.sleep(2)  # Allow ranges to load
        
        # Check that morph-type field has the correct value from LIFT
        morph_type_select = Select(chrome_driver.find_element(By.ID, 'morph-type'))
        current_value = morph_type_select.first_selected_option.get_attribute('value')
        
        # Should be 'stem' as set in LIFT data, not auto-classified
        assert current_value != '', "Morph-type should have a value from LIFT data"
        
        # Now modify the lexical unit to something that would trigger auto-classification
        lexical_unit_field = chrome_driver.find_element(By.ID, 'lexical-unit')
        lexical_unit_field.clear()
        lexical_unit_field.send_keys('pre-')  # Would normally auto-classify as 'prefix'
        
        # Trigger the input event
        chrome_driver.execute_script("arguments[0].dispatchEvent(new Event('input', {bubbles: true}));", lexical_unit_field)
        time.sleep(1)
        
        # Check that morph-type was NOT changed to 'prefix'
        morph_type_select = Select(chrome_driver.find_element(By.ID, 'morph-type'))
        new_value = morph_type_select.first_selected_option.get_attribute('value')
        
        # The morph-type should still be 'stem', not auto-classified as 'prefix'
        assert new_value == current_value, f"Morph-type should not be auto-overridden. Expected {current_value}, got {new_value}"
    
    @pytest.mark.selenium  
    @pytest.mark.integration
    def test_empty_morph_type_gets_auto_classified(self, chrome_driver, test_app, dict_service_with_db: DictionaryService, flask_test_server):
        """Test that entries with no morph-type get auto-classified"""
        # Clean up any existing test entries
        try:
            existing = dict_service_with_db.get_entry('test-morph-456')
            if existing:
                dict_service_with_db.delete_entry('test-morph-456')
        except Exception:
            pass  # Entry doesn't exist, which is fine
        
        # Create an entry with no morph-type
        entry_data = {
            'id_': 'test-morph-456',
            'lexical_unit': {'en': 'test-suffix'},
            'morph_type': '',  # Empty - should be auto-classified
            'senses': [{'id': 'sense1', 'glosses': {'en': 'test definition'}}]
        }
        
        entry = Entry.from_dict(entry_data)
        dict_service_with_db.create_entry(entry)
        entry_id = entry.id
        
        wait = WebDriverWait(chrome_driver, 10)
        
        # Navigate to edit form
        chrome_driver.get(f'{flask_test_server}/entries/{entry_id}/edit')
        
        # Wait for page to load and ranges to be populated
        wait.until(EC.presence_of_element_located((By.ID, 'lexical-unit')))
        time.sleep(2)
        
        # Check that morph-type field is auto-classified as 'suffix' 
        morph_type_select = Select(chrome_driver.find_element(By.ID, 'morph-type'))
        current_value = morph_type_select.first_selected_option.get_attribute('value')
        
        print(f"Auto-classified morph-type for 'test-suffix': {current_value}")
        
        # Should be auto-classified as suffix or contain 'suffix'
        option_text = morph_type_select.first_selected_option.text.lower()
        assert 'suffix' in option_text or 'suffix' in current_value.lower(), \
            f"Expected 'suffix' classification for 'test-suffix', got: {option_text}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
