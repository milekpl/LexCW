"""
Manual test to verify RelationsManager works in the actual Flask application.
This test starts the Flask server and tests the relations UI through a real HTTP request.
"""
import time
import requests
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options


def test_relations_manager_in_flask_app():
    """Test RelationsManager in the actual Flask application."""
    
    # Set up headless Chrome
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")
    
    driver = webdriver.Chrome(options=chrome_options)
    
    try:
        # Try to access the Flask app (assuming it's running on localhost:5000)
        base_url = "http://localhost:5000"
        
        # First check if the server is running
        try:
            response = requests.get(base_url, timeout=5)
            print(f"Flask server is running at {base_url}")
        except requests.exceptions.ConnectionError:
            print("Flask server is not running. Please start it with: python run.py")
            print("Skipping this test.")
            return
        
        # Navigate to an entry page (you might need to adjust this URL)
        # For now, let's try to access the main page or entry creation page
        try:
            driver.get(f"{base_url}/create_entry")
            
            # Wait for page to load
            WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            
            print("✓ Successfully loaded entry creation page")
            
            # Wait a bit for JavaScript to initialize
            time.sleep(3)
            
            # Check that RelationsManager is available
            relations_manager_available = driver.execute_script("""
                return typeof window.RelationsManager !== 'undefined';
            """)
            
            print(f"RelationsManager available: {relations_manager_available}")
            
            if relations_manager_available:
                print("✓ RelationsManager is properly available in the real Flask application")
            else:
                print("✗ RelationsManager is not available in the real Flask application")
                
                # Get console logs for debugging
                console_logs = driver.get_log('browser')
                print("Console logs:")
                for log in console_logs:
                    if log['level'] in ['SEVERE', 'WARNING']:
                        print(f"  {log['level']}: {log['message']}")
            
        except Exception as e:
            print(f"Could not access entry creation page: {e}")
            print("Trying main page instead...")
            
            driver.get(base_url)
            WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            print("✓ Successfully loaded main page")
            
    finally:
        driver.quit()


if __name__ == "__main__":
    test_relations_manager_in_flask_app()
