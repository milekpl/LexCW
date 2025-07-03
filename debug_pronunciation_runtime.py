#!/usr/bin/env python3
"""
Debug script to check what's happening with pronunciation rendering at runtime.
"""

import sys
sys.path.insert(0, '.')

from app import create_app
from app.services.dictionary_service import DictionaryService
from app.database.db_connector import DatabaseConnector
import json

def debug_pronunciation_runtime():
    app = create_app()
    
    with app.app_context():
        # Get an entry with pronunciations
        service = DictionaryService()
        entries = service.get_entries(limit=10)
        
        entry_with_pronunciations = None
        for entry in entries:
            if hasattr(entry, 'pronunciations') and entry.pronunciations:
                entry_with_pronunciations = entry
                break
        
        if not entry_with_pronunciations:
            print("No entry with pronunciations found")
            return
        
        print(f"Found entry with pronunciations: {entry_with_pronunciations.id}")
        print(f"Pronunciations: {entry_with_pronunciations.pronunciations}")
        print(f"Type: {type(entry_with_pronunciations.pronunciations)}")
        
        # Try to render template and check JSON serialization
        try:
            # This is what happens in the template
            pronunciations_json = json.dumps(entry_with_pronunciations.pronunciations or {})
            print(f"JSON serialization: {pronunciations_json}")
            
            # Test the conversion logic from template
            pronunciations = entry_with_pronunciations.pronunciations or {}
            if pronunciations and isinstance(pronunciations, dict):
                pronunciation_array = []
                for writing_system, value in pronunciations.items():
                    pronunciation_array.append({
                        'type': writing_system,
                        'value': value,
                        'audio_file': '',
                        'is_default': True
                    })
                print(f"Converted array: {pronunciation_array}")
            
        except Exception as e:
            print(f"Error during template processing: {e}")
            import traceback
            traceback.print_exc()

if __name__ == '__main__':
    debug_pronunciation_runtime()
