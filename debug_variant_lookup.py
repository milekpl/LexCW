#!/usr/bin/env python3
"""
Debug script to check variant data enrichment
"""

import requests
import sys
from app import create_app
from app.services.dictionary_service import DictionaryService

def debug_variant_lookup():
    """Debug the variant data lookup issue."""
    
    print("=== Debugging Variant Data Lookup ===\n")
    
    # Create Flask app context
    app = create_app()
    
    with app.app_context():
        dict_service = app.injector.get(DictionaryService)
        
        # Test entry IDs mentioned by user
        source_entry_id = "Protestant ethic_64c53110-099c-446b-8e7f-e06517d47c92"
        target_entry_id = "Protestant work ethic_38cda8f9-199f-44b3-9bf0-bc2e08ba33bf"
        
        print(f"Source entry ID: {source_entry_id}")
        print(f"Target entry ID: {target_entry_id}")
        print()
        
        # 1. Check if both entries exist
        print("1. Checking if entries exist...")
        try:
            source_entry = dict_service.get_entry(source_entry_id)
            print(f"✅ Source entry found: {source_entry.lexical_unit if source_entry else 'None'}")
        except Exception as e:
            print(f"❌ Source entry not found: {e}")
            return False
        
        try:
            target_entry = dict_service.get_entry(target_entry_id)
            print(f"✅ Target entry found: {target_entry.lexical_unit if target_entry else 'None'}")
        except Exception as e:
            print(f"❌ Target entry not found: {e}")
            print("   This explains why the link is not created!")
            
            # Let's search for similar entries
            print("\n2. Searching for similar entries...")
            try:
                # Search for "Protestant work ethic"
                search_results = dict_service.search_entries("Protestant work ethic", limit=10)
                print(f"   Found {len(search_results)} results for 'Protestant work ethic':")
                for i, result in enumerate(search_results):
                    print(f"   {i+1}. {result.get('id')} -> {result.get('lexical_unit')}")
                    
                # Also search for entries with similar patterns
                search_results2 = dict_service.search_entries("work ethic", limit=10)
                print(f"\n   Found {len(search_results2)} results for 'work ethic':")
                for i, result in enumerate(search_results2):
                    print(f"   {i+1}. {result.get('id')} -> {result.get('lexical_unit')}")
                    
            except Exception as search_e:
                print(f"   Search failed: {search_e}")
            
            return False
        
        # 2. Check the raw variant relations
        print("\n3. Checking raw variant relations...")
        raw_variants = source_entry.variant_relations
        print(f"   Raw variant relations count: {len(raw_variants)}")
        for i, variant in enumerate(raw_variants):
            print(f"   {i+1}. {variant}")
        
        # 3. Check the enriched variant relations
        print("\n4. Checking enriched variant relations...")
        try:
            enriched_variants = source_entry.get_complete_variant_relations(dict_service)
            print(f"   Enriched variant relations count: {len(enriched_variants)}")
            for i, variant in enumerate(enriched_variants):
                print(f"   {i+1}. {variant}")
                
                # Check if ref_display_text is populated
                if 'ref_display_text' in variant:
                    print(f"       ✅ Has ref_display_text: {variant['ref_display_text']}")
                else:
                    print(f"       ❌ Missing ref_display_text")
                    
        except Exception as e:
            print(f"   ❌ Error getting enriched variants: {e}")
            import traceback
            traceback.print_exc()
            return False
        
        print("\n5. Testing the actual web request...")
        try:
            url = f"http://127.0.0.1:5000/entries/{source_entry_id}/edit"
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                print("   ✅ Web request successful")
                # Check if the error message appears in the HTML
                if "Target Entry Not Found" in response.text:
                    print("   ❌ 'Target Entry Not Found' error message found in HTML")
                elif "clickable link" in response.text or "href" in response.text:
                    print("   ✅ Links found in HTML")
                else:
                    print("   ⚠️  Unable to determine from HTML content")
            else:
                print(f"   ❌ Web request failed: {response.status_code}")
        except Exception as e:
            print(f"   ❌ Web request error: {e}")
        
        return True

if __name__ == "__main__":
    success = debug_variant_lookup()
    exit(0 if success else 1)
