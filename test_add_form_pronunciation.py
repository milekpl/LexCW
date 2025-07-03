#!/usr/bin/env python3
"""
Test to check if PronunciationFormsManager is working correctly by accessing the add entry form.
"""

import sys
sys.path.insert(0, '.')

import requests

def test_pronunciation_add_form():
    """Test if pronunciation form is working by checking the add entry form."""
    
    base_url = "http://localhost:5000"
    
    try:
        # Get the add entry form
        edit_url = f"{base_url}/entries/add"
        response = requests.get(edit_url)
        
        if response.status_code != 200:
            print(f"Could not access entry add form: {response.status_code}")
            return
        
        html = response.text
        
        # Check for key elements
        checks = [
            ('pronunciation-container', 'pronunciation-container found'),
            ('add-pronunciation-btn', 'add pronunciation button found'),
            ('PronunciationFormsManager', 'PronunciationFormsManager script found'),
            ('pronunciation-forms.js', 'pronunciation-forms.js script found'),
            ('const pronunciations = ', 'pronunciation data initialization found'),
            ('window.pronunciationFormsManager = new PronunciationFormsManager', 'PronunciationFormsManager initialization found'),
        ]
        
        for check, message in checks:
            if check in html:
                print(f"✓ {message}")
            else:
                print(f"✗ {message}")
        
        # Extract and show the pronunciation data passed to JavaScript
        import re
        pattern = r'const pronunciations = ({[^}]*});'
        match = re.search(pattern, html, re.DOTALL)
        if match:
            print(f"Pronunciation data passed to JS: {match.group(1)}")
        else:
            print("No pronunciation data initialization found")
        
        # Save the HTML for manual inspection
        with open('add_entry_form_debug.html', 'w', encoding='utf-8') as f:
            f.write(html)
        print("Saved add entry form HTML to add_entry_form_debug.html for inspection")
        
    except requests.exceptions.ConnectionError:
        print("Could not connect to the application. Make sure it's running on localhost:5000")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == '__main__':
    test_pronunciation_add_form()
