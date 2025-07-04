#!/usr/bin/env python3
"""
Test script to capture and analyze the actual DOM content to debug variant UI
"""

import requests
import re
from urllib.parse import quote

def analyze_variant_ui():
    print("=== ANALYZING VARIANT UI DOM CONTENT ===")
    
    # URL-encode the entry ID properly
    entry_id = "Protestant work ethic_38cda8f9-199f-44b3-9bf0-bc2e08ba33bf"
    encoded_id = quote(entry_id)
    url = f"http://localhost:5000/entries/{encoded_id}/edit"
    
    print(f"Testing URL: {url}")
    
    try:
        response = requests.get(url, timeout=10)
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            content = response.text
            
            print("\n=== VARIANT SECTION ANALYSIS ===")
            
            # Find the variants section
            variant_section_match = re.search(
                r'<div class="card mb-4">.*?<h5 class="mb-0">.*?Variants.*?</h5>.*?</div>.*?</div>.*?</div>',
                content, re.DOTALL
            )
            
            if variant_section_match:
                variant_section = variant_section_match.group(0)
                print("Found Variants section:")
                print("-" * 50)
                print(variant_section[:1000] + "..." if len(variant_section) > 1000 else variant_section)
                print("-" * 50)
                
                # Check for "No Variants Found"
                if "No Variants Found" in variant_section:
                    print("❌ Still showing 'No Variants Found'")
                else:
                    print("✅ Not showing 'No Variants Found'")
                    
                # Check for actual variant cards
                if "variant-item" in variant_section:
                    print("✅ Found variant-item elements")
                else:
                    print("❌ No variant-item elements found")
                    
            else:
                print("❌ Could not find Variants section")
                
            print("\n=== JAVASCRIPT ANALYSIS ===")
            
            # Check for variant data in JavaScript
            variant_data_match = re.search(r'window\.variantRelations = (\[.*?\]);', content, re.DOTALL)
            if variant_data_match:
                variant_data = variant_data_match.group(1)
                print(f"Found variant data: {variant_data}")
                if variant_data.strip() == "[]":
                    print("❌ Variant data is still empty!")
                else:
                    print("✅ Variant data found!")
            else:
                print("❌ No variant data found in JavaScript")
                
            # Check for VariantFormsManager initialization
            if "window.variantFormsManager = new VariantFormsManager" in content:
                print("✅ VariantFormsManager initialization found")
            else:
                print("❌ VariantFormsManager initialization not found")
                
            # Check for forceRender call
            if "forceRender" in content:
                print("✅ forceRender call found")
            else:
                print("❌ forceRender call not found")
                
            print("\n=== DEBUG OUTPUT ANALYSIS ===")
            
            # Look for debug console.log statements
            debug_logs = re.findall(r"console\.log\('[^']*DEBUG[^']*'[^)]*\);", content)
            print(f"Found {len(debug_logs)} debug log statements:")
            for i, log in enumerate(debug_logs[:5]):  # Show first 5
                print(f"  {i+1}: {log}")
                
        else:
            print(f"Error: HTTP {response.status_code}")
            print(response.text[:500])
            
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    analyze_variant_ui()
