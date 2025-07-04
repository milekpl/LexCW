#!/usr/bin/env python3
"""
Quick test to verify that the variant links fix is working correctly
"""

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time

def test_variant_links_fix():
    """Test that variant links are now working correctly without showing raw IDs."""
    
    # Setup headless Chrome
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    
    driver = webdriver.Chrome(options=chrome_options)
    wait = WebDriverWait(driver, 10)
    
    try:
        # Test the specific URL mentioned by the user
        test_url = "http://127.0.0.1:5000/entries/Protestant%20ethic_64c53110-099c-446b-8e7f-e06517d47c92/edit"
        print(f"Testing URL: {test_url}")
        
        driver.get(test_url)
        
        # Wait for the page to load
        wait.until(EC.presence_of_element_located((By.ID, "variants-container")))
        
        # Find the variants container
        variants_container = driver.find_element(By.ID, "variants-container")
        
        # Check if there are any visible text inputs showing raw IDs in variants
        text_inputs = variants_container.find_elements(By.CSS_SELECTOR, "input[type='text']")
        
        raw_id_found = False
        for input_field in text_inputs:
            value = input_field.get_attribute('value') or ''
            name = input_field.get_attribute('name') or ''
            
            # Check if this is a variant ref field showing a raw ID
            if 'variant_relations' in name and '[ref]' in name and value:
                print(f"❌ Found visible text input with raw ID: {name} = {value}")
                raw_id_found = True
            elif '_' in value and '-' in value and len(value) > 30:
                # Potential raw ID (GUID format)
                print(f"⚠️  Potential raw ID in input: {name} = {value}")
        
        if not raw_id_found:
            print("✅ No raw IDs found in visible text inputs!")
        
        # Check for clickable links
        variant_links = variants_container.find_elements(By.CSS_SELECTOR, "a[href*='/entries/']")
        if variant_links:
            for link in variant_links:
                if 'edit' in link.get_attribute('href'):
                    print(f"✅ Found clickable variant link: {link.text} -> {link.get_attribute('href')}")
        else:
            print("⚠️  No clickable variant links found")
        
        # Check for hidden inputs (should contain the IDs)
        hidden_inputs = variants_container.find_elements(By.CSS_SELECTOR, "input[type='hidden']")
        hidden_refs_found = 0
        for hidden_input in hidden_inputs:
            name = hidden_input.get_attribute('name') or ''
            value = hidden_input.get_attribute('value') or ''
            if 'variant_relations' in name and '[ref]' in name and value:
                print(f"✅ Found hidden input with ID (correctly hidden): {name}")
                hidden_refs_found += 1
        
        print(f"✅ Found {hidden_refs_found} hidden variant ref inputs")
        
        # Check for search interfaces
        search_inputs = variants_container.find_elements(By.CSS_SELECTOR, "input.variant-search-input")
        if search_inputs:
            print(f"✅ Found {len(search_inputs)} variant search interfaces")
        else:
            print("❌ No variant search interfaces found")
        
        success = not raw_id_found and len(variant_links) > 0 and hidden_refs_found > 0
        
        if success:
            print("\n🎉 Variant links fix verified successfully!")
        else:
            print("\n❌ Variant links fix verification failed!")
            
        return success
        
    except Exception as e:
        print(f"❌ Error during test: {e}")
        return False
        
    finally:
        driver.quit()

if __name__ == "__main__":
    success = test_variant_links_fix()
    exit(0 if success else 1)
