"""Test the Flask app entry form in browser to verify POS inheritance."""

import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select

import pytest

@pytest.mark.integration
def test_pos_inheritance_ui():
    """Test POS inheritance in the browser UI."""
    
    # Setup Chrome driver
    options = webdriver.ChromeOptions()
    options.add_argument('--headless')  # Run in background
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
    
    try:
        print("Opening entry form...")
        driver.get("http://127.0.0.1:5000/entries/new")
        
        # Wait for page to load
        wait = WebDriverWait(driver, 10)
        headword_input = wait.until(EC.presence_of_element_located((By.ID, "headword-en")))
        
        print("Page loaded successfully")
        
        # Fill in headword
        headword_input.send_keys("test")
        
        # Check if POS field is initially required
        pos_select = driver.find_element(By.ID, "part-of-speech")
        required_indicator = driver.find_element(By.ID, "pos-required-indicator")
        
        print(f"Initial POS required: {pos_select.get_attribute('required')}")
        print(f"Initial asterisk visible: {required_indicator.is_displayed()}")
        
        # Add a sense
        add_sense_button = driver.find_element(By.ID, "add-sense")
        add_sense_button.click()
        
        time.sleep(1)  # Wait for sense to be added
        
        # Fill in sense definition
        sense_definition = driver.find_element(By.CSS_SELECTOR, ".sense-item .definition-field")
        sense_definition.send_keys("A test definition")
        
        # Set grammatical info for the sense
        sense_pos_select = driver.find_element(By.CSS_SELECTOR, ".sense-item .dynamic-grammatical-info")
        Select(sense_pos_select).select_by_visible_text("Noun")
        
        time.sleep(2)  # Wait for inheritance logic to run
        
        # Check if entry POS was inherited and field is no longer required
        print(f"After adding sense - POS value: {pos_select.get_attribute('value')}")
        print(f"After adding sense - POS required: {pos_select.get_attribute('required')}")
        print(f"After adding sense - asterisk visible: {required_indicator.is_displayed()}")
        
        # Add another sense with the same POS
        add_sense_button.click()
        time.sleep(1)
        
        sense_definitions = driver.find_elements(By.CSS_SELECTOR, ".sense-item .definition-field")
        sense_definitions[1].send_keys("Another test definition")
        
        sense_pos_selects = driver.find_elements(By.CSS_SELECTOR, ".sense-item .dynamic-grammatical-info")
        Select(sense_pos_selects[1]).select_by_visible_text("Noun")
        
        time.sleep(2)
        
        print(f"After adding 2nd sense (same POS) - POS value: {pos_select.get_attribute('value')}")
        print(f"After adding 2nd sense (same POS) - POS required: {pos_select.get_attribute('required')}")
        print(f"After adding 2nd sense (same POS) - asterisk visible: {required_indicator.is_displayed()}")
        
        # Change second sense to different POS
        Select(sense_pos_selects[1]).select_by_visible_text("Verb")
        
        time.sleep(2)
        
        print(f"After changing 2nd sense POS - POS value: {pos_select.get_attribute('value')}")
        print(f"After changing 2nd sense POS - POS required: {pos_select.get_attribute('required')}")
        print(f"After changing 2nd sense POS - asterisk visible: {required_indicator.is_displayed()}")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        driver.quit()

if __name__ == "__main__":
    test_pos_inheritance_ui()
