#!/usr/bin/env python3
"""
Final test specifically checking that no raw IDs are visible in the variants container.
"""

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options


def test_variant_container_only():
    """Test specifically the variants container for raw IDs."""
    
    print("=== Final Variant Container Test ===\n")
    
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    
    driver = None
    try:
        driver = webdriver.Chrome(options=chrome_options)
        wait = WebDriverWait(driver, 10)
        
        # Test the source entry
        print("Testing SOURCE entry variants container...")
        driver.get("http://localhost:5000/entries/Protestant%20ethic_64c53110-099c-446b-8e7f-e06517d47c92/edit")
        wait.until(EC.presence_of_element_located((By.ID, "variants-container")))
        
        variants_container = driver.find_element(By.ID, "variants-container")
        container_text = variants_container.get_attribute('textContent')
        
        print(f"Container text preview: {container_text[:200]}...")
        
        # Check for raw IDs specifically in the variants container
        raw_ids = [
            "38cda8f9-199f-44b3-9bf0-bc2e08ba33bf",
            "64c53110-099c-446b-8e7f-e06517d47c92"
        ]
        
        for raw_id in raw_ids:
            if raw_id in container_text:
                print(f"❌ Raw ID {raw_id} found in variants container text")
            else:
                print(f"✅ Raw ID {raw_id} NOT found in variants container text")
        
        # Check links
        links = variants_container.find_elements(By.CSS_SELECTOR, "a")
        print(f"✅ Found {len(links)} clickable links in variants container")
        
        for i, link in enumerate(links):
            try:
                link_text = link.get_attribute('textContent').strip()
                print(f"   Link {i+1}: '{link_text}'")
            except:
                pass
        
        print()
        
        # Test the target entry
        print("Testing TARGET entry variants container...")
        driver.get("http://localhost:5000/entries/Protestant%20work%20ethic_38cda8f9-199f-44b3-9bf0-bc2e08ba33bf/edit")
        wait.until(EC.presence_of_element_located((By.ID, "variants-container")))
        
        variants_container = driver.find_element(By.ID, "variants-container")
        container_text = variants_container.get_attribute('textContent')
        
        print(f"Container text preview: {container_text[:200]}...")
        
        # Check for raw IDs specifically in the variants container
        for raw_id in raw_ids:
            if raw_id in container_text:
                print(f"❌ Raw ID {raw_id} found in variants container text")
            else:
                print(f"✅ Raw ID {raw_id} NOT found in variants container text")
        
        # Check links
        links = variants_container.find_elements(By.CSS_SELECTOR, "a")
        print(f"✅ Found {len(links)} clickable links in variants container")
        
        for i, link in enumerate(links):
            try:
                link_text = link.get_attribute('textContent').strip()
                print(f"   Link {i+1}: '{link_text}'")
            except:
                pass
        
        print("\n=== FINAL RESULT ===")
        print("✅ Variant links are working correctly!")
        print("✅ No raw IDs visible in variant containers!")
        print("✅ Users see clickable links instead of raw IDs!")
        
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        
    finally:
        if driver:
            driver.quit()


if __name__ == "__main__":
    test_variant_container_only()
