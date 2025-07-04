#!/usr/bin/env python3
"""
Debug script to check what's happening with variant UI
"""

import requests
from bs4 import BeautifulSoup
import re

print("=== DEBUGGING VARIANT UI ===")

# Test the edit form for Protestant work ethic
url = "http://localhost:5000/entries/Protestant%20work%20ethic_38cda8f9-199f-44b3-9bf0-bc2e08ba33bf/edit"
print(f"Testing URL: {url}")

try:
    response = requests.get(url, timeout=5)
    print(f"Status Code: {response.status_code}")
    
    if response.status_code == 200:
        content = response.text
        
        # Check if variant data is in the HTML
        variant_data_match = re.search(r'window\.variantRelations = (\[.*?\]);', content, re.DOTALL)
        if variant_data_match:
            variant_data = variant_data_match.group(1)
            print(f"Found variant data in HTML: {variant_data}")
        else:
            print("NO variant data found in HTML!")
        
        # Check if VariantFormsManager is being initialized
        if "window.variantFormsManager = new VariantFormsManager" in content:
            print("✅ VariantFormsManager initialization found")
        else:
            print("❌ VariantFormsManager initialization NOT found")
            
        # Check if forceRender is being called
        if "forceRender" in content:
            print("✅ forceRender call found")
        else:
            print("❌ forceRender call NOT found")
            
        # Check for variant-forms.js script inclusion
        if "variant-forms.js" in content:
            print("✅ variant-forms.js script included")
        else:
            print("❌ variant-forms.js script NOT included")
            
        # Look for the variants container
        if 'id="variants-container"' in content:
            print("✅ variants-container found")
        else:
            print("❌ variants-container NOT found")
            
        # Check for debug console logs
        console_log_count = content.count("console.log")
        print(f"Number of console.log statements: {console_log_count}")
        
    else:
        print(f"Error: HTTP {response.status_code}")
        print(response.text)
        
except Exception as e:
    print(f"Error connecting to Flask app: {e}")
    print("Make sure the Flask app is running on localhost:5000")
