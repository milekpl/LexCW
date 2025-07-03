#!/usr/bin/env python3
"""
Test the DictionaryService within the Flask app context to see if variant data loads correctly
"""

from app import create_app

app = create_app()

with app.app_context():
    from flask import current_app
    from app.services.dictionary_service import DictionaryService
    
    print("=== TESTING DICTIONARY SERVICE IN FLASK CONTEXT ===")
    
    # Get the properly configured DictionaryService from the injector
    dict_service = current_app.injector.get(DictionaryService)
    print(f"DictionaryService: {dict_service}")
    print(f"Database connector: {dict_service.db_connector}")
    print(f"Database name: {getattr(dict_service.db_connector, 'database', 'No database attr')}")
    
    # Test loading the entry
    entry_id = 'Protestant work ethic_38cda8f9-199f-44b3-9bf0-bc2e08ba33bf'
    print(f"\nLoading entry: {entry_id}")
    
    try:
        entry = dict_service.get_entry(entry_id)
        if entry:
            print(f"✅ Entry loaded: {entry.id}")
            print(f"✅ Variant relations count: {len(entry.variant_relations)}")
            for i, variant in enumerate(entry.variant_relations):
                print(f"  Variant {i+1}: {variant}")
                
            if len(entry.variant_relations) > 0:
                print("✅ Backend is working correctly!")
                print("❌ So the issue must be in the template or JavaScript timing!")
            else:
                print("❌ Backend is not loading variant relations!")
        else:
            print("❌ Entry not found!")
    except Exception as e:
        print(f"❌ Error loading entry: {e}")
        import traceback
        traceback.print_exc()
