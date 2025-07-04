"""
Debug Network Requests

This script checks what network requests are being made and their status.
"""

import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


def debug_network():
    """Debug network requests."""
    
    # Set up Chrome with network logging
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")
    
    # Enable logging
    chrome_options.add_experimental_option('useAutomationExtension', False)
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_argument('--enable-logging')
    chrome_options.add_argument('--log-level=0')
    
    try:
        driver = webdriver.Chrome(options=chrome_options)
        driver.implicitly_wait(10)
    except Exception as e:
        print(f"Chrome WebDriver not available: {e}")
        return
    
    try:
        # Enable Performance logging
        driver.execute_cdp_cmd('Performance.enable', {})
        driver.execute_cdp_cmd('Network.enable', {})
        
        # Navigate to the entry edit page
        url = "http://127.0.0.1:5000/entries/Protestant%20work%20ethic_38cda8f9-199f-44b3-9bf0-bc2e08ba33bf/edit"
        print(f"Loading URL: {url}")
        driver.get(url)
        
        # Wait for the page to load
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        
        # Wait for scripts to load
        time.sleep(5)
        
        print("=== Network Requests ===")
        
        # Get network logs
        logs = driver.get_log('performance')
        
        for log in logs:
            message = log.get('message')
            if 'Network.responseReceived' in str(message):
                try:
                    import json
                    log_data = json.loads(message)
                    response_data = log_data.get('message', {}).get('params', {}).get('response', {})
                    url = response_data.get('url', '')
                    status = response_data.get('status', '')
                    
                    if '.js' in url or 'variant' in url or 'relation' in url:
                        print(f"JS File: {url.split('/')[-1]} - Status: {status}")
                except:
                    pass
        
        # Check what scripts are actually loaded
        print("\n=== Loaded Scripts ===")
        scripts = driver.execute_script("""
            var scripts = document.querySelectorAll('script[src]');
            var result = [];
            for (var i = 0; i < scripts.length; i++) {
                result.push(scripts[i].src);
            }
            return result;
        """)
        
        for script in scripts:
            if '.js' in script:
                script_name = script.split('/')[-1]
                print(f"Script: {script_name}")
        
        # Check if specific classes are available
        print("\n=== Class Availability ===")
        classes = ['VariantFormsManager', 'RelationsManager', 'PronunciationFormsManager']
        for class_name in classes:
            available = driver.execute_script(f"return typeof window.{class_name} !== 'undefined';")
            print(f"{class_name}: {'Available' if available else 'Not Available'}")
        
        # Check console errors
        print("\n=== Console Logs (All) ===")
        console_logs = driver.get_log('browser')
        for log in console_logs:
            print(f"{log['level']}: {log['message']}")
        
    finally:
        driver.quit()


if __name__ == "__main__":
    debug_network()
