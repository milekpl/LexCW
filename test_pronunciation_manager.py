#!/usr/bin/env python3
"""
Test if the pronunciation forms manager is working in the browser.
"""

import requests
from bs4 import BeautifulSoup

def test_pronunciation_manager():
    """Test pronunciation manager loading."""
    url = "http://127.0.0.1:5000/entries/Protestant1_8c895a90-6c91-4257-8ada-528e18d2ba69/edit"
    response = requests.get(url)
    
    if response.status_code != 200:
        print(f"Error: {response.status_code}")
        return
    
    soup = BeautifulSoup(response.text, 'html.parser')
    
    # Check if the pronunciation forms JS is included
    scripts = soup.find_all('script', src=True)
    pronunciation_js_found = False
    
    for script in scripts:
        if 'pronunciation-forms.js' in script['src']:
            pronunciation_js_found = True
            print(f"✓ Found pronunciation-forms.js: {script['src']}")
    
    if not pronunciation_js_found:
        print("❌ pronunciation-forms.js not found!")
    
    # Check if the container exists
    container = soup.find('div', {'id': 'pronunciation-container'})
    if container:
        print("✓ Found pronunciation container")
        
        # Check if any pronunciation items are already rendered
        pronunciation_items = container.find_all('div', class_='pronunciation-item')
        print(f"Found {len(pronunciation_items)} pronunciation items in HTML")
        
    else:
        print("❌ Pronunciation container not found!")
    
    # Check for add button
    add_btn = soup.find('button', {'id': 'add-pronunciation-btn'})
    if add_btn:
        print("✓ Found add pronunciation button")
    else:
        print("❌ Add pronunciation button not found!")

if __name__ == '__main__':
    test_pronunciation_manager()
