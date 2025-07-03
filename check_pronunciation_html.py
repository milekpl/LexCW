#!/usr/bin/env python3
"""
Test the HTML output of the entry form to see if pronunciations are being passed correctly.
"""

import requests
from bs4 import BeautifulSoup
import re

def test_pronunciation_in_html():
    """Test if pronunciation data is in the HTML."""
    url = "http://127.0.0.1:5000/entries/Protestant1_8c895a90-6c91-4257-8ada-528e18d2ba69/edit"
    response = requests.get(url)
    
    if response.status_code != 200:
        print(f"Error: {response.status_code}")
        return
    
    soup = BeautifulSoup(response.text, 'html.parser')
    
    # Find the script with pronunciation data
    scripts = soup.find_all('script')
    for script in scripts:
        if script.string and 'pronunciations' in script.string:
            print("Found pronunciation script:")
            print(script.string)
            print("\n" + "="*50 + "\n")
            
            # Check for the pronunciation container
            container = soup.find('div', {'id': 'pronunciation-container'})
            if container:
                print("Found pronunciation container:")
                print(container.prettify())
            else:
                print("ERROR: Pronunciation container not found!")
            
            return
    
    print("ERROR: No pronunciation script found!")

if __name__ == '__main__':
    test_pronunciation_in_html()
