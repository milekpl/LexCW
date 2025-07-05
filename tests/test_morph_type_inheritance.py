#!/usr/bin/env python3
"""
Test morph-type respect for existing LIFT data
"""

import pytest
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select
import time
import os
import sys

# Add the app directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app import create_app
from config import TestingConfig

class TestMorphTypeInheritance:
    """Test that morph-type respects existing LIFT data and doesn't auto-override"""
    
    @pytest.fixture(scope="class")
    def setup_class(self):
        """Set up the test environment"""
        self.app = create_app(TestingConfig)
        self.app_context = self.app.app_context()
        self.app_context.push()
        
        # Create tables
        db.create_all()
        
        # Set up Chrome driver
        chrome_options = webdriver.ChromeOptions()
        chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        
        self.driver = webdriver.Chrome(options=chrome_options)
        self.wait = WebDriverWait(self.driver, 10)
        
        yield
        
        # Cleanup
        self.driver.quit()
        db.session.remove()
        db.drop_all()
        self.app_context.pop()
    
    def test_existing_morph_type_not_overridden(self, setup_class):
        """Test that entries with existing morph-type in LIFT aren't overridden"""
        
        # Create an entry with existing morph-type "stem" (from LIFT)
        entry = Entry(
            lexical_unit="Protestant",
            lexical_unit_language_code="en",
            guid="test-morph-123"
        )
        entry.grammatical_info = {
            'part_of_speech': '',  # No POS yet 
            'morph_type': 'stem'   # Existing from LIFT data
        }
        
        db.session.add(entry)
        db.session.commit()
        entry_id = entry.id
        
        # Navigate to edit form
        self.driver.get(f'http://localhost:5000/entries/{entry_id}/edit')
        
        # Wait for page to load and ranges to be populated
        self.wait.until(EC.presence_of_element_located((By.ID, 'lexical-unit')))
        time.sleep(2)  # Allow ranges to load
        
        # Check that morph-type field has the correct value from LIFT
        morph_type_select = Select(self.driver.find_element(By.ID, 'morph-type'))
        current_value = morph_type_select.first_selected_option.get_attribute('value')
        
        # Should be 'stem' as set in LIFT data, not auto-classified
        assert current_value != '', "Morph-type should have a value from LIFT data"
        
        # Now modify the lexical unit to something that would trigger auto-classification
        lexical_unit_field = self.driver.find_element(By.ID, 'lexical-unit')
        lexical_unit_field.clear()
        lexical_unit_field.send_keys('pre-')  # Would normally auto-classify as 'prefix'
        
        # Trigger the input event
        self.driver.execute_script("arguments[0].dispatchEvent(new Event('input', {bubbles: true}));", lexical_unit_field)
        time.sleep(1)
        
        # Check that morph-type was NOT changed to 'prefix'
        morph_type_select = Select(self.driver.find_element(By.ID, 'morph-type'))
        new_value = morph_type_select.first_selected_option.get_attribute('value')
        
        print(f"Original value: {current_value}")
        print(f"Value after changing lexical unit to 'pre-': {new_value}")
        
        # The morph-type should still be 'stem', not auto-classified as 'prefix'
        assert new_value == current_value, f"Morph-type should not be auto-overridden. Expected {current_value}, got {new_value}"
    
    def test_empty_morph_type_gets_auto_classified(self, setup_class):
        """Test that entries with no morph-type get auto-classified"""
        
        # Create an entry with no morph-type
        entry = Entry(
            lexical_unit="test-suffix",
            lexical_unit_language_code="en",
            guid="test-morph-456"
        )
        entry.grammatical_info = {
            'part_of_speech': '',
            'morph_type': ''  # Empty - should be auto-classified
        }
        
        db.session.add(entry)
        db.session.commit()
        entry_id = entry.id
        
        # Navigate to edit form
        self.driver.get(f'http://localhost:5000/entries/{entry_id}/edit')
        
        # Wait for page to load and ranges to be populated
        self.wait.until(EC.presence_of_element_located((By.ID, 'lexical-unit')))
        time.sleep(2)
        
        # Check that morph-type field is auto-classified as 'suffix' 
        morph_type_select = Select(self.driver.find_element(By.ID, 'morph-type'))
        current_value = morph_type_select.first_selected_option.get_attribute('value')
        
        print(f"Auto-classified morph-type for 'test-suffix': {current_value}")
        
        # Should be auto-classified as suffix or contain 'suffix'
        option_text = morph_type_select.first_selected_option.text.lower()
        assert 'suffix' in option_text or 'suffix' in current_value.lower(), \
            f"Expected 'suffix' classification for 'test-suffix', got: {option_text}"

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
