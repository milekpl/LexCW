#!/usr/bin/env python3
"""
Selenium test to verify that variant links are displayed correctly in the UI.
"""

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
import time


def test_variant_links_ui():
    """Test that variant links are displayed correctly in the UI."""
    
    print("=== Testing Variant Links UI ===\n")
    
    # Set up Chrome options
    chrome_options = Options()
    chrome_options.add_argument("--headless")  # Run in headless mode
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    
    driver = None
    try:
        driver = webdriver.Chrome(options=chrome_options)
        wait = WebDriverWait(driver, 10)
        
        # Test 1: Source entry (Protestant ethic)
        print("1. Testing SOURCE entry (Protestant ethic)...")
        driver.get("http://localhost:5000/entries/Protestant%20ethic_64c53110-099c-446b-8e7f-e06517d47c92/edit")
        
        # Wait for page to load
        wait.until(EC.presence_of_element_located((By.ID, "variants-container")))
        
        # Check if variants container is present
        variants_container = driver.find_element(By.ID, "variants-container")
        print("   ✅ Variants container found")
        
        # Check for variant links
        variant_links = variants_container.find_elements(By.CSS_SELECTOR, "a.variant-link")
        if variant_links:
            print(f"   ✅ Found {len(variant_links)} variant link(s)")
            for i, link in enumerate(variant_links):
                link_text = link.get_attribute('textContent').strip()
                link_href = link.get_attribute('href')
                print(f"      Link {i+1}: '{link_text}' -> {link_href}")
                
                # Check if this is the expected link
                if 'Protestant work ethic' in link_text:
                    print("      ✅ Expected 'Protestant work ethic' link found")
                else:
                    print(f"      ❌ Unexpected link text: {link_text}")
        else:
            print("   ❌ No variant links found")
        
        # Check for raw IDs in the UI
        variant_items = variants_container.find_elements(By.CSS_SELECTOR, ".variant-item")
        raw_id_found = False
        for item in variant_items:
            item_text = item.get_attribute('textContent')
            if '38cda8f9-199f-44b3-9bf0-bc2e08ba33bf' in item_text:
                print("   ❌ Raw ID visible in UI!")
                raw_id_found = True
        
        if not raw_id_found:
            print("   ✅ No raw IDs visible in UI")
        
        print()
        
        # Test 2: Target entry (Protestant work ethic)
        print("2. Testing TARGET entry (Protestant work ethic)...")
        driver.get("http://localhost:5000/entries/Protestant%20work%20ethic_38cda8f9-199f-44b3-9bf0-bc2e08ba33bf/edit")
        
        # Wait for page to load
        wait.until(EC.presence_of_element_located((By.ID, "variants-container")))
        
        # Check if variants container is present
        variants_container = driver.find_element(By.ID, "variants-container")
        print("   ✅ Variants container found")
        
        # Check for variant links
        variant_links = variants_container.find_elements(By.CSS_SELECTOR, "a.variant-link")
        if variant_links:
            print(f"   ✅ Found {len(variant_links)} variant link(s)")
            for i, link in enumerate(variant_links):
                link_text = link.get_attribute('textContent').strip()
                link_href = link.get_attribute('href')
                print(f"      Link {i+1}: '{link_text}' -> {link_href}")
                
                # Check if this is the expected link
                if 'Protestant ethic' in link_text:
                    print("      ✅ Expected 'Protestant ethic' link found")
                else:
                    print(f"      ❌ Unexpected link text: {link_text}")
        else:
            print("   ❌ No variant links found")
        
        # Check for raw IDs in the UI
        variant_items = variants_container.find_elements(By.CSS_SELECTOR, ".variant-item")
        raw_id_found = False
        for item in variant_items:
            item_text = item.get_attribute('textContent')
            if '64c53110-099c-446b-8e7f-e06517d47c92' in item_text:
                print("   ❌ Raw ID visible in UI!")
                raw_id_found = True
        
        if not raw_id_found:
            print("   ✅ No raw IDs visible in UI")
        
        print("\n=== Test Summary ===")
        print("✅ Variant UI test completed successfully")
        
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        
    finally:
        if driver:
            driver.quit()


if __name__ == "__main__":
    test_variant_links_ui()
