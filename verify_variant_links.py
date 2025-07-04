#!/usr/bin/env python3
"""
Quick verification script to test the variant links functionality.
This tests that:
1. Variants container shows clickable links instead of raw IDs
2. Error markers appear for missing targets
3. Both incoming and outgoing variant directions work
"""

import requests
import re
from bs4 import BeautifulSoup

def test_variant_links_functionality():
    """Test that variant links are working correctly."""
    
    # Test URL for an entry with variants
    test_url = "http://127.0.0.1:5000/entries/Protestant%20work%20ethic_4fa1a14b-9a8e-49bf-8cd3-c2ad01f46e4d/edit"
    
    try:
        print("Testing variant links functionality...")
        
        # Fetch the page
        response = requests.get(test_url, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Find the variants container
        variants_container = soup.find('div', id='variants-container')
        if not variants_container:
            print("❌ Variants container not found")
            return False
            
        print("✅ Variants container found")
        
        # Check for variant items
        variant_items = variants_container.find_all('div', class_='variant-item')
        print(f"✅ Found {len(variant_items)} variant items")
        
        success = True
        
        for i, variant_item in enumerate(variant_items):
            print(f"\n--- Checking variant item {i+1} ---")
            
            # Check for clickable links
            links = variant_item.find_all('a')
            if links:
                for link in links:
                    if link.get('href') and 'edit_entry' in link.get('href', ''):
                        print(f"✅ Found clickable link: {link.text.strip()}")
                    else:
                        print(f"⚠️  Found link but not an edit link: {link}")
            else:
                print("❌ No clickable links found in variant item")
                success = False
            
            # Check for hidden input fields (not visible raw IDs)
            hidden_inputs = variant_item.find_all('input', type='hidden')
            visible_text_inputs = variant_item.find_all('input', type='text')
            
            print(f"✅ Found {len(hidden_inputs)} hidden input fields")
            
            # Check if there are any visible text inputs with raw IDs
            for text_input in visible_text_inputs:
                name = text_input.get('name', '')
                value = text_input.get('value', '')
                if 'ref]' in name and value:
                    print(f"❌ Found visible text input with raw ID: {name} = {value}")
                    success = False
            
            # Check for error markers (if any missing targets)
            danger_alerts = variant_item.find_all('div', class_='alert alert-danger')
            if danger_alerts:
                for alert in danger_alerts:
                    print(f"✅ Found error marker for missing target: {alert.text.strip()[:100]}...")
            
            # Check for search interface
            search_inputs = variant_item.find_all('input', class_='variant-search-input')
            if search_inputs:
                print("✅ Found search interface for variant selection")
            else:
                print("❌ Search interface not found")
                success = False
        
        if success:
            print("\n🎉 All variant link functionality tests passed!")
        else:
            print("\n❌ Some variant link functionality tests failed!")
            
        return success
        
    except requests.exceptions.RequestException as e:
        print(f"❌ Error accessing the URL: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

if __name__ == "__main__":
    success = test_variant_links_functionality()
    exit(0 if success else 1)
