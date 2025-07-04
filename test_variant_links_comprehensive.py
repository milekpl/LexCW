#!/usr/bin/env python3
"""
Comprehensive test script to verify that the variant UI displays clickable links correctly
for both outgoing and incoming variant relations.
"""

import requests
import re


def test_variant_links_comprehensive():
    """Test variant links for both directions."""
    
    # Source entry (has outgoing variant to Protestant work ethic)
    source_url = "http://localhost:5000/entries/Protestant%20ethic_64c53110-099c-446b-8e7f-e06517d47c92/edit"
    
    # Target entry (has incoming variant from Protestant ethic)
    target_url = "http://localhost:5000/entries/Protestant%20work%20ethic_38cda8f9-199f-44b3-9bf0-bc2e08ba33bf/edit"
    
    print("=== Testing Comprehensive Variant Links ===\n")
    
    # Test source entry (outgoing variant)
    print("1. Testing SOURCE entry (outgoing variant)...")
    try:
        response = requests.get(source_url, timeout=10)
        
        if response.status_code == 200:
            content = response.text
            
            # Check variant data
            variant_data_match = re.search(r'const variantRelations = (\[.*?\]);', content, re.DOTALL)
            if variant_data_match:
                variant_data = variant_data_match.group(1)
                print(f"   ✅ Variant data found: {variant_data}")
                
                # Check for expected target reference
                if 'Protestant work ethic_38cda8f9-199f-44b3-9bf0-bc2e08ba33bf' in variant_data:
                    print("   ✅ Target variant reference found")
                else:
                    print("   ❌ Target variant reference NOT found")
                    
                # Check for direction
                if '"direction": "outgoing"' in variant_data:
                    print("   ✅ Outgoing direction found")
                else:
                    print("   ❌ Outgoing direction NOT found")
                    
                # Check for display text
                if 'Protestant work ethic' in variant_data:
                    print("   ✅ Display text found")
                else:
                    print("   ❌ Display text NOT found")
            else:
                print("   ❌ No variant data found")
                
        else:
            print(f"   ❌ HTTP Error: {response.status_code}")
            
    except requests.exceptions.RequestException as e:
        print(f"   ❌ Request failed: {e}")
    
    print()
    
    # Test target entry (incoming variant)
    print("2. Testing TARGET entry (incoming variant)...")
    try:
        response = requests.get(target_url, timeout=10)
        
        if response.status_code == 200:
            content = response.text
            
            # Check variant data
            variant_data_match = re.search(r'const variantRelations = (\[.*?\]);', content, re.DOTALL)
            if variant_data_match:
                variant_data = variant_data_match.group(1)
                print(f"   ✅ Variant data found: {variant_data}")
                
                # Check for expected source reference
                if 'Protestant ethic_64c53110-099c-446b-8e7f-e06517d47c92' in variant_data:
                    print("   ✅ Source variant reference found")
                else:
                    print("   ❌ Source variant reference NOT found")
                    
                # Check for direction
                if '"direction": "incoming"' in variant_data:
                    print("   ✅ Incoming direction found")
                else:
                    print("   ❌ Incoming direction NOT found")
                    
                # Check for display text
                if 'Protestant ethic' in variant_data:
                    print("   ✅ Display text found")
                else:
                    print("   ❌ Display text NOT found")
            else:
                print("   ❌ No variant data found")
                
        else:
            print(f"   ❌ HTTP Error: {response.status_code}")
            
    except requests.exceptions.RequestException as e:
        print(f"   ❌ Request failed: {e}")
    
    print()
    
    # Test for visible raw IDs in HTML (these should NOT be present)
    print("3. Testing for hidden raw IDs...")
    for name, url in [("SOURCE", source_url), ("TARGET", target_url)]:
        try:
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                content = response.text
                
                # Look for raw ID patterns in visible HTML (outside of script tags)
                # Remove script tags first
                html_without_scripts = re.sub(r'<script.*?</script>', '', content, flags=re.DOTALL)
                
                # Look for the raw UUID patterns in the remaining HTML
                raw_id_pattern = r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}'
                raw_ids = re.findall(raw_id_pattern, html_without_scripts)
                
                if raw_ids:
                    print(f"   ❌ {name}: Found visible raw IDs: {raw_ids}")
                else:
                    print(f"   ✅ {name}: No visible raw IDs found")
                    
        except requests.exceptions.RequestException as e:
            print(f"   ❌ {name}: Request failed: {e}")


if __name__ == "__main__":
    test_variant_links_comprehensive()
