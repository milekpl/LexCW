#!/usr/bin/env python3
"""
Debug script to check which entry ID is being used and what variant data is returned
"""

import requests
import re

print("=== DEBUGGING ENTRY ID AND VARIANT DATA ===")

# Let's try different URLs to see which ones work
urls_to_test = [
    "http://localhost:5000/entries/Protestant%20work%20ethic_38cda8f9-199f-44b3-9bf0-bc2e08ba33bf/edit",
    "http://localhost:5000/entries/Protestant%20work%20ethic/edit",
    "http://localhost:5000/entries/Protestant work ethic_38cda8f9-199f-44b3-9bf0-bc2e08ba33bf/edit"
]

for url in urls_to_test:
    print(f"\nTesting URL: {url}")
    try:
        response = requests.get(url, timeout=5)
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            content = response.text
            
            # Extract the entry ID from the HTML
            entry_id_match = re.search(r'data-entry-id="([^"]*)"', content)
            if entry_id_match:
                actual_entry_id = entry_id_match.group(1)
                print(f"Found entry ID in HTML: {actual_entry_id}")
            
            # Check variant data
            variant_data_match = re.search(r'window\.variantRelations = (\[.*?\]);', content, re.DOTALL)
            if variant_data_match:
                variant_data = variant_data_match.group(1)
                print(f"Variant data: {variant_data}")
                if variant_data.strip() == "[]":
                    print("❌ Variant data is empty!")
                else:
                    print("✅ Variant data found!")
            else:
                print("❌ No variant data found in HTML!")
                
        elif response.status_code == 404:
            print("❌ Entry not found (404)")
        else:
            print(f"❌ Error: HTTP {response.status_code}")
            
    except Exception as e:
        print(f"❌ Error: {e}")

print("\n" + "="*50)
print("Now let's test our backend directly...")

# Test our backend script to see what variant data it finds
import subprocess
result = subprocess.run(['python', 'test_variant_parsing.py'], 
                       capture_output=True, text=True, cwd='.')
if result.returncode == 0:
    output = result.stdout
    if "Protestant work ethic" in output and "Variant Relations: 1" in output:
        print("✅ Backend script shows variants exist!")
        print("❌ But web interface shows empty variant data!")
        print("🔍 This means the issue is in how the web view loads the entry!")
    else:
        print("❌ Backend script shows no variants")
else:
    print(f"❌ Backend script failed: {result.stderr}")
