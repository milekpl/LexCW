#!/usr/bin/env python3
"""
Test to check if LIFT ranges are properly loaded in the entry form.
This test verifies that the ranges loader is initialized correctly and that
the main form elements are populated with LIFT ranges.
"""

import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import Select

def test_entry_form_lift_ranges_population():
    """Test that LIFT ranges are populated in the entry form dropdowns"""
    
    # Set up Chrome options for headless testing
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    
    driver = webdriver.Chrome(options=chrome_options)
    
    try:
        # Navigate to the add entry form
        driver.get("http://localhost:5000/entries/add")
        
        # Wait for the page to load
        wait = WebDriverWait(driver, 10)
        
        # Wait for ranges loader to be available
        wait.until(lambda d: d.execute_script("return typeof window.rangesLoader !== 'undefined'"))
        
        # Wait for the part-of-speech select element
        part_of_speech_select = wait.until(
            EC.presence_of_element_located((By.ID, "part-of-speech"))
        )
        
        # Wait a bit longer for ranges to be loaded
        time.sleep(2)
        
        # Check if the part-of-speech select has been populated with options
        select_element = Select(part_of_speech_select)
        options = select_element.options
        
        # Should have more than just the default option
        assert len(options) > 1, f"Part of speech select should have more than 1 option, found {len(options)}"
        
        # Check if we have some expected grammatical options
        option_texts = [opt.text for opt in options]
        print(f"Part of speech options found: {option_texts}")
        
        # Should contain at least some basic parts of speech
        expected_options = ['Noun', 'Verb', 'Adjective', 'Adverb']
        found_options = [opt for opt in expected_options if opt in option_texts]
        
        assert len(found_options) > 0, f"Should find at least some basic parts of speech, found: {found_options}"
        
        # Test the ranges API directly
        print("Testing ranges API...")
        
        # Get the actual response
        ranges_response = driver.execute_script("""
            return window.lastRangesResponse || null;
        """)
        
        print(f"Ranges API response: {ranges_response}")
        
        # Test pronunciation handling
        lexical_unit_input = driver.find_element(By.ID, "lexical-unit")
        lexical_unit_input.send_keys("test")
        
        # Check if pronunciation section is visible
        pronunciation_section = driver.find_element(By.ID, "pronunciation-container")
        assert pronunciation_section.is_displayed(), "Pronunciation section should be visible"
        
        print("Entry form LIFT ranges population test passed!")
        
    except Exception as e:
        print(f"Test failed with error: {e}")
        # Take a screenshot for debugging
        driver.save_screenshot("entry_form_error.png")
        raise
    finally:
        driver.quit()

if __name__ == "__main__":
    test_entry_form_lift_ranges_population()
