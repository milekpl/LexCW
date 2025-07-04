"""
Simple Network Debug

Check if scripts are loading and available.
"""

import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


def debug_simple():
    """Simple debug of script loading."""
    
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
        url = "http://127.0.0.1:5000/entries/Protestant%20work%20ethic_38cda8f9-199f-44b3-9bf0-bc2e08ba33bf/edit"
        print(f"Loading URL: {url}")
        driver.get(url)
        
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        
        time.sleep(5)  # Wait for scripts to load
        
        # Check what scripts are loaded
        print("=== Loaded Scripts ===")
        scripts = driver.execute_script("""
            var scripts = document.querySelectorAll('script[src]');
            var result = [];
            for (var i = 0; i < scripts.length; i++) {
                var src = scripts[i].src;
                if (src.includes('.js')) {
                    result.push(src.split('/').pop());
                }
            }
            return result;
        """)
        
        for script in scripts:
            print(f"  {script}")
        
        # Check classes
        print("\n=== Class Availability ===")
        classes = {
            'VariantFormsManager': driver.execute_script("return typeof window.VariantFormsManager;"),
            'RelationsManager': driver.execute_script("return typeof window.RelationsManager;"),
            'RangesLoader': driver.execute_script("return typeof window.RangesLoader;")
        }
        
        for class_name, type_result in classes.items():
            print(f"  {class_name}: {type_result}")
        
        # Check if variant manager was created
        print("\n=== Manager Instances ===")
        instances = {
            'variantFormsManager': driver.execute_script("return typeof window.variantFormsManager;"),
            'relationsManager': driver.execute_script("return typeof window.relationsManager;"),
        }
        
        for instance_name, type_result in instances.items():
            print(f"  {instance_name}: {type_result}")
        
        # Check debug data
        print("\n=== Debug Data ===")
        variant_relations = driver.execute_script("return window.variantRelations;")
        print(f"  window.variantRelations: {variant_relations}")
        
        # Check browser logs
        print("\n=== Console Logs ===")
        logs = driver.get_log('browser')
        for log in logs:
            if 'TEMPLATE DEBUG' in log['message'] or 'VARIANT DEBUG' in log['message']:
                print(f"  {log['level']}: {log['message']}")
        
    finally:
        driver.quit()


if __name__ == "__main__":
    debug_simple()
