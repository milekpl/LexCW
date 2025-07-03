#!/usr/bin/env python3
"""
Test script to verify JavaScript execution and ranges/pronunciation display.
This uses Selenium to actually test the browser rendering.
"""

import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


def test_javascript_execution():
    """Test that JavaScript properly initializes ranges and pronunciations."""
    
    # Setup Chrome with headless option for automated testing
    chrome_options = Options()
    chrome_options.add_argument("--headless")  # Run in background
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    
    driver = None
    try:
        driver = webdriver.Chrome(options=chrome_options)
        
        # Navigate to the entry edit form
        url = "http://localhost:5000/entries/AIDS%20test_a774b9c4-c013-4f54-9017-cf818791080c/edit"
        print(f"Loading URL: {url}")
        driver.get(url)
        
        # Wait for page to load
        wait = WebDriverWait(driver, 10)
        wait.until(EC.presence_of_element_located((By.ID, "pronunciation-container")))
        
        print("✅ Page loaded successfully")
        
        # Check if window.rangesLoader exists
        ranges_loader_exists = driver.execute_script("return typeof window.rangesLoader !== 'undefined';")
        print(f"window.rangesLoader exists: {'✅' if ranges_loader_exists else '❌'}")
        
        # Check if pronunciation manager exists
        pron_manager_exists = driver.execute_script("return typeof window.pronunciationFormsManager !== 'undefined';")
        print(f"window.pronunciationFormsManager exists: {'✅' if pron_manager_exists else '❌'}")
        
        # Check if pronunciation container has content
        pron_container = driver.find_element(By.ID, "pronunciation-container")
        pron_content = pron_container.get_attribute("innerHTML").strip()
        has_pron_content = len(pron_content) > 50  # Should have actual content, not just comments
        print(f"Pronunciation container has content: {'✅' if has_pron_content else '❌'}")
        
        if not has_pron_content:
            print(f"Pronunciation container content: {pron_content[:200]}...")
        
        # Check if semantic domain select has options
        try:
            semantic_domain_select = driver.find_element(By.ID, "semantic-domain-ddp4")
            options = semantic_domain_select.find_elements(By.TAG_NAME, "option")
            has_options = len(options) > 1  # Should have more than just the default option
            print(f"Semantic domain select has options: {'✅' if has_options else '❌'} ({len(options)} options)")
        except Exception as e:
            print(f"❌ Could not find semantic domain select: {e}")
        
        # Check if grammatical info select has options
        try:
            gram_info_select = driver.find_element(By.ID, "part-of-speech")
            options = gram_info_select.find_elements(By.TAG_NAME, "option")
            has_options = len(options) > 1
            print(f"Grammatical info select has options: {'✅' if has_options else '❌'} ({len(options)} options)")
        except Exception as e:
            print(f"❌ Could not find grammatical info select: {e}")
        
        # Wait a bit for any async operations
        time.sleep(2)
        
        # Re-check pronunciation container after waiting
        pron_content_after = pron_container.get_attribute("innerHTML").strip()
        has_pron_content_after = len(pron_content_after) > 50
        print(f"Pronunciation container has content (after wait): {'✅' if has_pron_content_after else '❌'}")
        
        if not has_pron_content_after:
            print(f"Pronunciation container content (after wait): {pron_content_after[:200]}...")
        
        # Check console for JavaScript errors
        logs = driver.get_log('browser')
        js_errors = [log for log in logs if log['level'] == 'SEVERE']
        if js_errors:
            print(f"❌ JavaScript errors found:")
            for error in js_errors:
                print(f"   {error['message']}")
        else:
            print("✅ No JavaScript errors found")
        
        # Save page source for debugging
        with open('browser_debug.html', 'w', encoding='utf-8') as f:
            f.write(driver.page_source)
        print("💾 Browser page source saved to browser_debug.html")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False
    finally:
        if driver:
            driver.quit()
    
    return True


if __name__ == '__main__':
    print("=== TESTING JAVASCRIPT EXECUTION IN BROWSER ===")
    test_javascript_execution()
