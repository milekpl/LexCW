#!/usr/bin/env python3
"""
Test to check if PronunciationFormsManager is working correctly in browser.
"""

import sys
sys.path.insert(0, '.')

import requests
from urllib.parse import urljoin
import time

def test_pronunciation_in_browser():
    """Test if pronunciation form is working by checking the actual HTML response."""
    
    base_url = "http://localhost:5000"
    
    # First, get the entries list to find an entry ID
    try:
        response = requests.get(f"{base_url}/entries")
        if response.status_code != 200:
            print(f"Could not access entries page: {response.status_code}")
            return
        
        # Find an entry link in the HTML
        html = response.text
        import re
        
        # Look for edit links - try multiple patterns
        edit_links = re.findall(r'/entries/(\d+)/edit', html)
        if not edit_links:
            # Try alternative patterns
            edit_links = re.findall(r'href="[^"]*entries/([^/"]+)/edit"', html)
        if not edit_links:
            # Try with view links instead
            view_links = re.findall(r'/entries/([^/"]+)', html)
            if view_links:
                entry_id = view_links[0]
                print(f"Found view link, will try edit form for entry: {entry_id}")
            else:
                print("No entry links found in entries page")
                # Save the HTML to debug
                with open('entries_page_debug.html', 'w', encoding='utf-8') as f:
                    f.write(html)
                print("Saved entries page HTML to entries_page_debug.html for inspection")
                return
        else:
            entry_id = edit_links[0]
        print(f"Testing with entry ID: {entry_id}")
        
        # Get the entry edit form
        edit_url = f"{base_url}/entries/{entry_id}/edit"
        response = requests.get(edit_url)
        
        if response.status_code != 200:
            print(f"Could not access entry edit form: {response.status_code}")
            return
        
        html = response.text
        
        # Check for key elements
        checks = [
            ('pronunciation-container', 'pronunciation-container found'),
            ('add-pronunciation-btn', 'add pronunciation button found'),
            ('PronunciationFormsManager', 'PronunciationFormsManager script found'),
            ('pronunciation-forms.js', 'pronunciation-forms.js script found'),
            ('const pronunciations = ', 'pronunciation data initialization found'),
        ]
        
        for check, message in checks:
            if check in html:
                print(f"✓ {message}")
            else:
                print(f"✗ {message}")
        
        # Extract and show the pronunciation data passed to JavaScript
        import re
        pattern = r'const pronunciations = ({.*?});'
        match = re.search(pattern, html, re.DOTALL)
        if match:
            print(f"Pronunciation data passed to JS: {match.group(1)}")
        else:
            print("No pronunciation data initialization found")
        
    except requests.exceptions.ConnectionError:
        print("Could not connect to the application. Make sure it's running on localhost:5000")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == '__main__':
    test_pronunciation_in_browser()
