#!/usr/bin/env python3
"""
Test script to check if pronunciations are working in the browser.
"""

from app import create_app
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time


def test_pronunciation_javascript():
    """Test pronunciation JavaScript execution in a real browser."""
    print("=== TESTING PRONUNCIATION JAVASCRIPT ===")
    
    app = create_app()
    
    # Start Flask app in a thread
    import threading
    from werkzeug.serving import make_server
    
    server = make_server('127.0.0.1', 5000, app)
    server_thread = threading.Thread(target=server.serve_forever)
    server_thread.daemon = True
    server_thread.start()
    
    time.sleep(2)  # Give server time to start
    
    # Setup Chrome browser
    chrome_options = Options()
    chrome_options.add_argument("--headless")  # Run in background
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    
    try:
        driver = webdriver.Chrome(options=chrome_options)
        
        # Navigate to entry form
        test_entry_id = "AIDS%20test_a774b9c4-c013-4f54-9017-cf818791080c"
        url = f"http://127.0.0.1:5000/entries/{test_entry_id}/edit"
        driver.get(url)
        
        # Wait for page to load
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "pronunciation-container"))
        )
        
        # Check if PronunciationFormsManager exists
        pronunciation_manager_exists = driver.execute_script(
            "return typeof window.pronunciationFormsManager !== 'undefined';"
        )
        print(f"✅ PronunciationFormsManager exists: {pronunciation_manager_exists}")
        
        # Check pronunciation container content
        container_html = driver.find_element(By.ID, "pronunciation-container").get_attribute('innerHTML')
        print(f"📄 Container HTML: {container_html[:200]}...")
        
        # Check if pronunciation inputs exist
        pronunciation_inputs = driver.find_elements(By.CSS_SELECTOR, ".pronunciation-item .ipa-input")
        print(f"🎯 Found {len(pronunciation_inputs)} pronunciation input fields")
        
        if pronunciation_inputs:
            for i, input_field in enumerate(pronunciation_inputs):
                value = input_field.get_attribute('value')
                print(f"   Input {i}: value='{value}'")
        
        # Check if ranges loader exists
        ranges_loader_exists = driver.execute_script(
            "return typeof window.rangesLoader !== 'undefined';"
        )
        print(f"✅ RangesLoader exists: {ranges_loader_exists}")
        
        # Check select elements
        selects = driver.find_elements(By.CSS_SELECTOR, "select[data-range-id]")
        print(f"🎯 Found {len(selects)} range select elements")
        
        for select in selects:
            range_id = select.get_attribute('data-range-id')
            options = select.find_elements(By.TAG_NAME, "option")
            print(f"   Select[{range_id}]: {len(options)} options")
        
        # Take a screenshot for debugging
        driver.save_screenshot("debug_entry_form.png")
        print("📸 Screenshot saved as debug_entry_form.png")
        
    except Exception as e:
        print(f"❌ Browser test failed: {e}")
    finally:
        try:
            driver.quit()
        except:
            pass
        server.shutdown()


if __name__ == '__main__':
    test_pronunciation_javascript()
