#!/usr/bin/env python3
"""
Test script to examine variant relations in specific entries from the LIFT file.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from app.services.dictionary_service import DictionaryService

def test_variant_entries():
    """Test specific entries that should have variant relations."""
    app = create_app()
    
    with app.app_context():
        dict_service = app.injector.get(DictionaryService)
        
        # Test the Protestant ethic entries
        test_entries = [
            "Protestant ethic_64c53110-099c-446b-8e7f-e06517d47c92",
            "Protestant work ethic_38cda8f9-199f-44b3-9bf0-bc2e08ba33bf",
            "protested draft_337e6c08-7903-4c99-868b-ec60483ae50b",
            "protestor_5b2d8179-ccc6-4aac-a21e-ef2a28bafb89"
        ]
        
        for entry_id in test_entries:
            print(f"\n=== Testing Entry: {entry_id} ===")
            try:
                entry = dict_service.get_entry(entry_id)
                print(f"Lexical Unit: {entry.lexical_unit}")
                print(f"Relations count: {len(entry.relations)}")
                
                # Examine each relation
                for i, relation in enumerate(entry.relations):
                    print(f"\nRelation {i+1}:")
                    print(f"  Type: {relation.type}")
                    print(f"  Ref: {relation.ref}")
                    print(f"  Traits: {getattr(relation, 'traits', {})}")
                    print(f"  Order: {getattr(relation, 'order', 'N/A')}")
                    
                    # Check if this is a variant relation
                    if hasattr(relation, 'traits') and relation.traits:
                        if 'variant-type' in relation.traits:
                            print(f"  >>> VARIANT TYPE: {relation.traits['variant-type']}")
                
                # Test the variant_relations property
                variant_relations = entry.variant_relations
                print(f"\nVariant Relations: {len(variant_relations)}")
                for i, variant in enumerate(variant_relations):
                    print(f"  Variant {i+1}: {variant}")
                    
            except Exception as e:
                print(f"Error processing {entry_id}: {e}")
        
        print("\n" + "="*50)
        print("Summary: Testing variant relation extraction")

if __name__ == "__main__":
    test_variant_entries()
