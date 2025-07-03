#!/usr/bin/env python3
"""
Test script to check if variant data is correctly passed to the template.
"""

import requests

def test_variant_in_template():
    """Test if variant data appears in the edit form."""
    url = "http://127.0.0.1:5000/entry/Protestant%20work%20ethic_38cda8f9-199f-44b3-9bf0-bc2e08ba33bf/edit"
    
    try:
        response = requests.get(url, timeout=30)
        if response.status_code == 200:
            content = response.text
            
            # Look for variant-related content
            print("=== Searching for variant-related content ===")
            
            # Check for variant container
            if 'variants-container' in content:
                print("✅ Found variants-container div")
            else:
                print("❌ variants-container div not found")
            
            # Check for variant relations data
            if 'variantRelations' in content:
                print("✅ Found variantRelations in JavaScript")
                # Extract the line with variantRelations
                lines = content.split('\n')
                for line in lines:
                    if 'variantRelations' in line:
                        print(f"   Line: {line.strip()}")
            else:
                print("❌ variantRelations not found in JavaScript")
            
            # Check for variant forms manager
            if 'VariantFormsManager' in content:
                print("✅ Found VariantFormsManager reference")
            else:
                print("❌ VariantFormsManager not found")
            
            # Check for variant sections
            if 'Variants (from Relations)' in content:
                print("✅ Found Variants section header")
            else:
                print("❌ Variants section header not found")
                
            # Check for empty state message
            if 'No Variant Relations' in content:
                print("⚠️ Found empty state message - variants might not be loading")
            else:
                print("✅ No empty state message found")
                
        else:
            print(f"❌ HTTP Error: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    test_variant_in_template()
