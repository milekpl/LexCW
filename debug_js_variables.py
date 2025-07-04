"""
Debug JavaScript Variables in Entry Form

This script checks what JavaScript variables are available and what values they have.
"""

import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


def debug_js_variables():
    """Debug JavaScript variables in the entry form."""
    
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
        
        # Wait for scripts to load
        time.sleep(3)
        
        print("=== Checking JavaScript Variables ===")
        
        # Check if window.variantRelations exists
        variant_relations = driver.execute_script("return typeof window.variantRelations !== 'undefined' ? window.variantRelations : 'undefined';")
        print(f"window.variantRelations: {variant_relations}")
        
        # Check if window.variantFormsManager exists
        variant_manager = driver.execute_script("return typeof window.variantFormsManager !== 'undefined' ? 'defined' : 'undefined';")
        print(f"window.variantFormsManager: {variant_manager}")
        
        # Check if VariantFormsManager class is available
        variant_class = driver.execute_script("return typeof window.VariantFormsManager !== 'undefined' ? 'defined' : 'undefined';")
        print(f"window.VariantFormsManager class: {variant_class}")
        
        # Check if relations manager exists
        relations_manager = driver.execute_script("return typeof window.relationsManager !== 'undefined' ? 'defined' : 'undefined';")
        print(f"window.relationsManager: {relations_manager}")
        
        # Check what's in the relations array for RelationsManager
        relations_array = driver.execute_script("return typeof window.relationsManager !== 'undefined' && window.relationsManager.relations ? window.relationsManager.relations : 'undefined';")
        print(f"RelationsManager.relations: {relations_array}")
        
        # Check containers
        variants_container = driver.execute_script("return document.getElementById('variants-container') ? 'exists' : 'not found';")
        print(f"variants-container element: {variants_container}")
        
        relations_container = driver.execute_script("return document.getElementById('relations-container') ? 'exists' : 'not found';")
        print(f"relations-container element: {relations_container}")
        
        # Check console for any errors
        print("\n=== Console Logs ===")
        logs = driver.get_log('browser')
        for log in logs:
            if log['level'] in ['SEVERE', 'WARNING']:
                print(f"{log['level']}: {log['message']}")
        
        # Check if we can manually access variant data
        print("\n=== Checking Template Variables ===")
        
        # Try to get the raw variant relations data from the script tags or global scope
        template_data = driver.execute_script("""
            // Look for any variant-related data in various locations
            var result = {};
            
            // Check all script tags for variant data
            var scripts = document.querySelectorAll('script');
            for (var i = 0; i < scripts.length; i++) {
                var script = scripts[i];
                if (script.innerHTML.includes('variantRelations') || script.innerHTML.includes('variant_relations')) {
                    result.foundInScript = true;
                    result.scriptContent = script.innerHTML.substring(0, 500) + '...';
                    break;
                }
            }
            
            // Check if entry data is available
            if (typeof entryData !== 'undefined') {
                result.entryData = entryData;
            }
            
            if (typeof window.entry !== 'undefined') {
                result.windowEntry = window.entry;
            }
            
            return result;
        """)
        print(f"Template data search: {template_data}")
        
        print("\n✅ JavaScript variable debugging completed!")
        
    finally:
        driver.quit()


if __name__ == "__main__":
    debug_js_variables()
