#!/usr/bin/env python3
"""
Debug script to check JavaScript console output and verify variant rendering.
"""

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
import time


def debug_variant_rendering():
    """Debug variant rendering in the browser."""
    
    print("=== Debugging Variant Rendering ===\n")
    
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--enable-logging")
    chrome_options.add_argument("--log-level=0")
    
    driver = None
    try:
        driver = webdriver.Chrome(options=chrome_options)
        wait = WebDriverWait(driver, 10)
        
        # Test the source entry
        print("Testing SOURCE entry (Protestant ethic)...")
        driver.get("http://localhost:5000/entries/Protestant%20ethic_64c53110-099c-446b-8e7f-e06517d47c92/edit")
        
        # Wait for page to load
        wait.until(EC.presence_of_element_located((By.ID, "variants-container")))
        
        # Get console logs
        console_logs = driver.get_log('browser')
        print("Console logs:")
        for log in console_logs:
            if 'VARIANT DEBUG' in log['message'] or 'error' in log['level'].lower():
                print(f"  {log['level']}: {log['message']}")
        
        # Check if window.variantRelations is defined
        variant_relations_js = driver.execute_script("return window.variantRelations;")
        print(f"\nwindow.variantRelations: {variant_relations_js}")
        
        # Check if VariantFormsManager exists
        manager_exists = driver.execute_script("return typeof VariantFormsManager !== 'undefined';")
        print(f"VariantFormsManager exists: {manager_exists}")
        
        # Check container content
        variants_container = driver.find_element(By.ID, "variants-container")
        container_html = variants_container.get_attribute('innerHTML')
        print(f"\nContainer HTML (first 500 chars): {container_html[:500]}...")
        
        # Count variant items
        variant_items = variants_container.find_elements(By.CSS_SELECTOR, ".variant-item")
        print(f"Variant items found: {len(variant_items)}")
        
        # Check for empty state
        empty_state = variants_container.find_elements(By.CSS_SELECTOR, ".empty-state")
        print(f"Empty state shown: {len(empty_state) > 0}")
        
        # Check for variant links
        variant_links = variants_container.find_elements(By.CSS_SELECTOR, "a")
        print(f"Links found in container: {len(variant_links)}")
        for link in variant_links:
            try:
                link_text = link.get_attribute('textContent')
                link_href = link.get_attribute('href')
                print(f"  Link: '{link_text}' -> {link_href}")
            except:
                pass
        
        # Try to manually trigger rendering
        print("\nManually triggering variant rendering...")
        driver.execute_script("""
            if (window.variantFormsManager) {
                console.log('[MANUAL DEBUG] Triggering renderExistingVariants()');
                window.variantFormsManager.renderExistingVariants();
            } else {
                console.log('[MANUAL DEBUG] variantFormsManager not found');
            }
        """)
        
        time.sleep(1)  # Wait for render
        
        # Check again after manual trigger
        console_logs = driver.get_log('browser')
        print("\nConsole logs after manual trigger:")
        for log in console_logs[-10:]:  # Last 10 logs
            if 'VARIANT DEBUG' in log['message'] or 'MANUAL DEBUG' in log['message'] or 'error' in log['level'].lower():
                print(f"  {log['level']}: {log['message']}")
        
        variant_items = variants_container.find_elements(By.CSS_SELECTOR, ".variant-item")
        print(f"Variant items after manual trigger: {len(variant_items)}")
        
    except Exception as e:
        print(f"❌ Debug failed with error: {e}")
        
    finally:
        if driver:
            driver.quit()


if __name__ == "__main__":
    debug_variant_rendering()
