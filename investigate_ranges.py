#!/usr/bin/env python3
"""
Detailed investigation of ranges loading issue.
"""

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time


def investigate_ranges_loading():
    """Investigate why ranges appear to not be loading."""
    
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    
    driver = None
    try:
        driver = webdriver.Chrome(options=chrome_options)
        
        url = "http://localhost:5000/entries/AIDS%20test_a774b9c4-c013-4f54-9017-cf818791080c/edit"
        driver.get(url)
        
        wait = WebDriverWait(driver, 10)
        wait.until(EC.presence_of_element_located((By.ID, "pronunciation-container")))
        
        # Wait for any async operations
        time.sleep(3)
        
        print("=== SEMANTIC DOMAIN INVESTIGATION ===")
        
        # Check raw select element
        semantic_select = driver.find_element(By.ID, "semantic-domain-ddp4")
        raw_options = semantic_select.find_elements(By.TAG_NAME, "option")
        print(f"Raw select options count: {len(raw_options)}")
        
        # Check for Select2 
        select2_elements = driver.find_elements(By.CSS_SELECTOR, "[data-select2-id]")
        print(f"Select2 elements found: {len(select2_elements)}")
        
        # Check if ranges loader completed
        loader_initialized = driver.execute_script("return window.rangesLoaderInitialized;")
        print(f"Ranges loader initialized: {loader_initialized}")
        
        # Check the rangesLoader cache
        cache_size = driver.execute_script("return window.rangesLoader ? window.rangesLoader.cache.size : 'not found';")
        print(f"RangesLoader cache size: {cache_size}")
        
        # Check console logs for ranges loading
        logs = driver.get_log('browser')
        ranges_logs = [log for log in logs if 'ranges' in log['message'].lower() or 'semantic' in log['message'].lower()]
        print(f"Ranges-related console logs: {len(ranges_logs)}")
        for log in ranges_logs:
            print(f"  {log['level']}: {log['message']}")
        
        # Check if semantic domain data was loaded
        semantic_data = driver.execute_script("""
            if (window.rangesLoader && window.rangesLoader.cache.has('semantic-domain-ddp4')) {
                return window.rangesLoader.cache.get('semantic-domain-ddp4');
            }
            return null;
        """)
        
        if semantic_data:
            print(f"✅ Semantic domain data found in cache with {len(semantic_data.get('values', []))} values")
        else:
            print("❌ No semantic domain data in cache")
        
        # Check actual HTML content of the select
        select_html = semantic_select.get_attribute('outerHTML')
        option_count = select_html.count('<option')
        print(f"HTML option tags count: {option_count}")
        
        # Save detailed debug info
        with open('select_debug.html', 'w', encoding='utf-8') as f:
            f.write(f"<h1>Semantic Domain Select Debug</h1>\n")
            f.write(f"<p>Raw options count: {len(raw_options)}</p>\n")
            f.write(f"<p>HTML option count: {option_count}</p>\n")
            f.write(f"<h2>Select HTML:</h2>\n")
            f.write(f"<pre>{select_html}</pre>\n")
        
        print("💾 Select debug saved to select_debug.html")
        
        print("\n=== GRAMMATICAL INFO INVESTIGATION ===")
        
        gram_select = driver.find_element(By.ID, "part-of-speech")
        gram_options = gram_select.find_elements(By.TAG_NAME, "option")
        print(f"Grammatical info options count: {len(gram_options)}")
        
        gram_data = driver.execute_script("""
            if (window.rangesLoader && window.rangesLoader.cache.has('grammatical-info')) {
                return window.rangesLoader.cache.get('grammatical-info');
            }
            return null;
        """)
        
        if gram_data:
            print(f"✅ Grammatical info data found in cache with {len(gram_data.get('values', []))} values")
        else:
            print("❌ No grammatical info data in cache")
        
        print("\n=== PRONUNCIATION INVESTIGATION ===")
        
        pron_container = driver.find_element(By.ID, "pronunciation-container")
        pron_html = pron_container.get_attribute('innerHTML')
        
        # Check for pronunciation input fields
        pron_inputs = pron_container.find_elements(By.CSS_SELECTOR, "input[name*='pronunciations']")
        print(f"Pronunciation input fields found: {len(pron_inputs)}")
        
        for i, input_elem in enumerate(pron_inputs):
            input_name = input_elem.get_attribute('name')
            input_value = input_elem.get_attribute('value')
            print(f"  Input {i+1}: {input_name} = '{input_value}'")
        
        # Check if pronunciation data was passed correctly
        pron_data_script = driver.execute_script("""
            // Look for the pronunciationData variable in the page
            const scripts = document.getElementsByTagName('script');
            for (let script of scripts) {
                if (script.innerHTML && script.innerHTML.includes('pronunciationData')) {
                    return script.innerHTML;
                }
            }
            return null;
        """)
        
        if pron_data_script:
            print("✅ Found pronunciationData in script")
            # Extract the data line
            lines = pron_data_script.split('\n')
            for line in lines:
                if 'pronunciationData' in line and '=' in line:
                    print(f"  Data: {line.strip()}")
                    break
        else:
            print("❌ pronunciationData not found in scripts")
            
    except Exception as e:
        print(f"❌ Investigation failed: {e}")
    finally:
        if driver:
            driver.quit()


if __name__ == '__main__':
    investigate_ranges_loading()
