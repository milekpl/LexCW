#!/usr/bin/env python3
"""
Debug pronunciation display in entry form.
"""

from app import create_app
from app.services.dictionary_service import DictionaryService
from flask import current_app

def debug_pronunciation_display():
    """Debug pronunciation display."""
    app = create_app()
    with app.app_context():
        dict_service = current_app.injector.get(DictionaryService)
        entry = dict_service.get_entry('Protestant1_8c895a90-6c91-4257-8ada-528e18d2ba69')
        
        print(f"Entry: {entry.lexical_unit}")
        print(f"Pronunciations: {entry.pronunciations}")
        print(f"Type: {type(entry.pronunciations)}")
        
        if entry.pronunciations:
            for lang, pron in entry.pronunciations.items():
                print(f"  {lang}: {pron}")
        else:
            print("  No pronunciations found")

if __name__ == '__main__':
    debug_pronunciation_display()
