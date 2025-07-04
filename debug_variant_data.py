#!/usr/bin/env python3
"""
Debug script to check what variant data is being passed to the template
"""

import requests
import json
from bs4 import BeautifulSoup
import re

def debug_variant_data():
    """Check what data is being passed to the template for variants."""
    
    # Test URL for the specific entry mentioned by the user
    test_url = "http://127.0.0.1:5000/entries/Protestant%20ethic_64c53110-099c-446b-8e7f-e06517d47c92/edit"
    
    try:
        print("Debugging variant data...")
        
        # Fetch the page
        response = requests.get(test_url, timeout=10)
        response.raise_for_status()
        
        content = response.text
        
        # Look for variant relations data in the JavaScript
        variant_data_match = re.search(r'const variant_relations = (\[.*?\]);', content, re.DOTALL)
        if variant_data_match:
            variant_data = variant_data_match.group(1)
            print(f"✅ Found variant_relations in JavaScript: {variant_data}")
            
            # Try to parse it as JSON
            try:
                parsed_data = json.loads(variant_data)
                print(f"✅ Parsed variant data: {json.dumps(parsed_data, indent=2)}")
                
                for i, variant in enumerate(parsed_data):
                    print(f"\n--- Variant {i+1} ---")
                    print(f"  ref: {variant.get('ref', 'N/A')}")
                    print(f"  ref_display_text: {variant.get('ref_display_text', 'N/A')}")
                    print(f"  ref_lexical_unit: {variant.get('ref_lexical_unit', 'N/A')}")
                    print(f"  variant_type: {variant.get('variant_type', 'N/A')}")
                    print(f"  direction: {variant.get('direction', 'N/A')}")
                    
            except json.JSONDecodeError as e:
                print(f"❌ Failed to parse variant data as JSON: {e}")
                
        else:
            print("❌ No variant_relations data found in JavaScript")
        
        # Also check the HTML content for any visible IDs
        soup = BeautifulSoup(content, 'html.parser')
        variants_container = soup.find('div', id='variants-container')
        
        if variants_container:
            print("\n=== Variants Container HTML ===")
            
            # Look for any text inputs that might be showing IDs
            text_inputs = variants_container.find_all('input', type='text')
            for input_field in text_inputs:
                name = input_field.get('name', '')
                value = input_field.get('value', '')
                if value and ('_' in value or '-' in value):  # Potential ID
                    print(f"❌ Found visible text input with potential ID: {name} = {value}")
            
            # Look for any elements showing raw IDs
            all_text = variants_container.get_text()
            if '_' in all_text and '-' in all_text:
                lines = all_text.split('\n')
                for line in lines:
                    line = line.strip()
                    if '_' in line and '-' in line and len(line) > 20:
                        print(f"⚠️  Potential raw ID in text: {line}")
        
        return True
        
    except requests.exceptions.RequestException as e:
        print(f"❌ Error accessing the URL: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

if __name__ == "__main__":
    debug_variant_data()
