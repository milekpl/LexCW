"""
Debug Relations and Variants UI

This script opens the entry page and checks what's displayed in both containers.
"""

import time
import sys
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


def debug_ui():
    """Debug the relations and variants UI."""
    
    # Set up headless Chrome
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")
    
    try:
        driver = webdriver.Chrome(options=chrome_options)
        driver.implicitly_wait(10)
    except Exception as e:
        print(f"Chrome WebDriver not available: {e}")
        return
    
    try:
        # Navigate to the entry edit page
        url = "http://127.0.0.1:5000/entries/Protestant%20work%20ethic_38cda8f9-199f-44b3-9bf0-bc2e08ba33bf/edit"
        print(f"Loading URL: {url}")
        driver.get(url)
        
        # Wait for the page to load
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        
        print("Page loaded successfully!")
        
        # Check page title
        title = driver.title
        print(f"Page title: {title}")
        
        # Look for variants container
        try:
            variants_container = driver.find_element(By.ID, "variants-container")
            print(f"✅ Found variants container")
            
            # Get all variant items
            variant_items = variants_container.find_elements(By.CLASS_NAME, "variant-item")
            print(f"Variant items found: {len(variant_items)}")
            
            if len(variant_items) == 0:
                # Check for empty state
                empty_state = variants_container.find_elements(By.CLASS_NAME, "empty-state")
                if empty_state:
                    print("Variants container shows empty state")
                    print(f"Empty state text: {empty_state[0].text}")
                else:
                    print("Variants container is empty but no empty state found")
                    print(f"Container content: {variants_container.text}")
                    
                # Check for any server-side rendered content
                server_content = variants_container.find_elements(By.CSS_SELECTOR, "[data-variant-index]")
                print(f"Server-side variant content: {len(server_content)} items")
                
        except Exception as e:
            print(f"❌ Error finding variants container: {e}")
        
        # Look for relations container
        try:
            relations_container = driver.find_element(By.ID, "relations-container")
            print(f"✅ Found relations container")
            
            # Get all relation items
            relation_items = relations_container.find_elements(By.CLASS_NAME, "relation-item")
            print(f"Relation items found: {len(relation_items)}")
            
            if len(relation_items) == 0:
                # Check for empty state
                empty_state = relations_container.find_elements(By.CLASS_NAME, "empty-state")
                if empty_state:
                    print("Relations container shows empty state")
                    print(f"Empty state text: {empty_state[0].text}")
                else:
                    print("Relations container is empty but no empty state found")
                    print(f"Container content: {relations_container.text}")
                    
        except Exception as e:
            print(f"❌ Error finding relations container: {e}")
        
        # Check for JavaScript errors in console
        logs = driver.get_log('browser')
        if logs:
            print("\n=== Browser Console Logs ===")
            for log in logs:
                print(f"{log['level']}: {log['message']}")
        else:
            print("No browser console errors found")
            
        # Wait a bit for any async JavaScript to complete
        time.sleep(3)
        
        # Re-check after waiting
        print("\n=== After waiting 3 seconds ===")
        
        variants_container = driver.find_element(By.ID, "variants-container")
        variant_items = variants_container.find_elements(By.CLASS_NAME, "variant-item")
        print(f"Variant items found: {len(variant_items)}")
        
        relations_container = driver.find_element(By.ID, "relations-container")
        relation_items = relations_container.find_elements(By.CLASS_NAME, "relation-item")
        print(f"Relation items found: {len(relation_items)}")
        
        # Take a screenshot for debugging
        try:
            driver.save_screenshot("debug_ui_screenshot.png")
            print("Screenshot saved as debug_ui_screenshot.png")
        except Exception as e:
            print(f"Could not save screenshot: {e}")
        
        print("\n✅ UI debugging completed!")
        
    finally:
        driver.quit()


if __name__ == "__main__":
    debug_ui()
