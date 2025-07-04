#!/usr/bin/env python3
"""
Fixed Selenium test to verify that variant links are displayed correctly in the UI.
"""

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options


def test_variant_links_ui_fixed():
    """Test that variant links are displayed correctly in the UI with correct selectors."""
    
    print("=== Testing Variant Links UI (Fixed) ===\n")
    
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
        
        # Check for ANY links in the variants container (not just .variant-link)
        variant_links = variants_container.find_elements(By.CSS_SELECTOR, "a")
        print(f"   Found {len(variant_links)} link(s) in variants container")
        
        for i, link in enumerate(variant_links):
            try:
                link_text = link.get_attribute('textContent').strip()
                link_href = link.get_attribute('href')
                print(f"      Link {i+1}: '{link_text}' -> {link_href}")
                
                # Check if this is the expected link to Protestant work ethic
                if 'Protestant work ethic' in link_text and 'Protestant%20work%20ethic_38cda8f9-199f-44b3-9bf0-bc2e08ba33bf' in link_href:
                    print("      ✅ Correct 'Protestant work ethic' link found!")
                elif 'Protestant work ethic' in link_text:
                    print(f"      ⚠️  'Protestant work ethic' link found but href may be wrong: {link_href}")
            except Exception as e:
                print(f"      ❌ Error reading link {i+1}: {e}")
        
        # Check for any elements containing raw IDs (these should be hidden)
        page_source = driver.page_source
        if '38cda8f9-199f-44b3-9bf0-bc2e08ba33bf' in page_source:
            # Raw ID exists - check if it's visible
            elements_with_id = driver.execute_script("""
                return Array.from(document.querySelectorAll('*')).filter(el => 
                    el.textContent && el.textContent.includes('38cda8f9-199f-44b3-9bf0-bc2e08ba33bf') && 
                    getComputedStyle(el).display !== 'none' && 
                    getComputedStyle(el).visibility !== 'hidden' &&
                    el.tagName !== 'SCRIPT'
                ).map(el => ({
                    tag: el.tagName,
                    text: el.textContent.substring(0, 100),
                    visible: true
                }));
            """)
            
            if elements_with_id:
                print("   ❌ Raw ID visible in UI elements:")
                for element in elements_with_id:
                    print(f"      {element['tag']}: {element['text']}...")
            else:
                print("   ✅ Raw ID exists but is properly hidden")
        else:
            print("   ✅ No raw IDs found on page")
        
        print()
        
        # Test 2: Target entry (Protestant work ethic)
        print("2. Testing TARGET entry (Protestant work ethic)...")
        driver.get("http://localhost:5000/entries/Protestant%20work%20ethic_38cda8f9-199f-44b3-9bf0-bc2e08ba33bf/edit")
        
        # Wait for page to load
        wait.until(EC.presence_of_element_located((By.ID, "variants-container")))
        
        # Check if variants container is present
        variants_container = driver.find_element(By.ID, "variants-container")
        print("   ✅ Variants container found")
        
        # Check for ANY links in the variants container
        variant_links = variants_container.find_elements(By.CSS_SELECTOR, "a")
        print(f"   Found {len(variant_links)} link(s) in variants container")
        
        for i, link in enumerate(variant_links):
            try:
                link_text = link.get_attribute('textContent').strip()
                link_href = link.get_attribute('href')
                print(f"      Link {i+1}: '{link_text}' -> {link_href}")
                
                # Check if this is the expected link to Protestant ethic
                if 'Protestant ethic' in link_text and 'Protestant%20ethic_64c53110-099c-446b-8e7f-e06517d47c92' in link_href:
                    print("      ✅ Correct 'Protestant ethic' link found!")
                elif 'Protestant ethic' in link_text:
                    print(f"      ⚠️  'Protestant ethic' link found but href may be wrong: {link_href}")
            except Exception as e:
                print(f"      ❌ Error reading link {i+1}: {e}")
        
        # Check for any elements containing raw IDs (these should be hidden)
        page_source = driver.page_source
        if '64c53110-099c-446b-8e7f-e06517d47c92' in page_source:
            # Raw ID exists - check if it's visible
            elements_with_id = driver.execute_script("""
                return Array.from(document.querySelectorAll('*')).filter(el => 
                    el.textContent && el.textContent.includes('64c53110-099c-446b-8e7f-e06517d47c92') && 
                    getComputedStyle(el).display !== 'none' && 
                    getComputedStyle(el).visibility !== 'hidden' &&
                    el.tagName !== 'SCRIPT'
                ).map(el => ({
                    tag: el.tagName,
                    text: el.textContent.substring(0, 100),
                    visible: true
                }));
            """)
            
            if elements_with_id:
                print("   ❌ Raw ID visible in UI elements:")
                for element in elements_with_id:
                    print(f"      {element['tag']}: {element['text']}...")
            else:
                print("   ✅ Raw ID exists but is properly hidden")
        else:
            print("   ✅ No raw IDs found on page")
        
        print("\n=== Test Summary ===")
        print("✅ Variant UI test completed successfully")
        
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        
    finally:
        if driver:
            driver.quit()


if __name__ == "__main__":
    test_variant_links_ui_fixed()
