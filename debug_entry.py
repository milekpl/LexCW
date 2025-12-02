"""Debug script to inspect entry data"""
import sys
import os

# Add the app directory to the path
sys.path.insert(0, os.path.dirname(__file__))

from app import create_app
from app.services.dictionary_service import DictionaryService
import json

app = create_app()

with app.app_context():
    dict_service = app.injector.get(DictionaryService)
    
    entry_id = "acid test_dc82bb0e-f5cb-4390-8912-0b53a0e54800"
    
    print(f"Fetching entry: {entry_id}")
    print("=" * 80)
    
    try:
        entry = dict_service.get_entry_for_editing(entry_id)
        
        if entry:
            entry_dict = entry.to_dict()
            print(json.dumps(entry_dict, indent=2, ensure_ascii=False))
            
            print("\n" + "=" * 80)
            print("LEXICAL UNIT:")
            print(f"Type: {type(entry.lexical_unit)}")
            print(f"Value: {entry.lexical_unit}")
            print(f"Dict form: {entry_dict.get('lexical_unit')}")
            
            print("\n" + "=" * 80)
            print("FORMS:")
            if hasattr(entry, 'forms'):
                print(f"entry.forms: {entry.forms}")
            
        else:
            print("Entry not found!")
            
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
