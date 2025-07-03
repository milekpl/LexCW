#!/usr/bin/env python3
"""
Test script to verify that the variant UI fix works correctly.
"""

import requests
import re

def test_variant_ui_fix():
    """Test that the variant UI now displays variants correctly."""
    
    # Test URL for an entry with variants
    test_url = "http://localhost:5000/entries/Protestant%20work%20ethic_38cda8f9-199f-44b3-9bf0-bc2e08ba33bf/edit"
    
    try:
        print("Testing variant UI fix...")
        
        response = requests.get(test_url, timeout=10)
        
        if response.status_code == 200:
            content = response.text
            
            # Check that variant data is being passed to JavaScript
            variant_data_match = re.search(r'const variantRelations = (\[.*?\]);', content, re.DOTALL)
            if variant_data_match:
                variant_data = variant_data_match.group(1)
                print(f"✅ Variant data found in template: {variant_data}")
                
                # Check if the data contains expected variant
                if 'Protestant ethic_64c53110-099c-446b-8e7f-e06517d47c92' in variant_data:
                    print("✅ Expected variant reference found in data")
                else:
                    print("❌ Expected variant reference NOT found in data")
                    
                if 'Unspecified Variant' in variant_data:
                    print("✅ Expected variant type found in data")
                else:
                    print("❌ Expected variant type NOT found in data")
            else:
                print("❌ No variant data found in template")
            
            # Check that VariantFormsManager is being initialized
            if 'VariantFormsManager' in content:
                print("✅ VariantFormsManager initialization code found")
            else:
                print("❌ VariantFormsManager initialization code NOT found")
                
            # Check that debug logging is present
            if 'forceRender' in content:
                print("✅ forceRender method call found")
            else:
                print("❌ forceRender method call NOT found")
                
        else:
            print(f"❌ HTTP Error: {response.status_code}")
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Request failed: {e}")

if __name__ == "__main__":
    test_variant_ui_fix()
