#!/usr/bin/env python3
"""
Quick script to list existing entry IDs for testing
"""

from app import create_app
from app.services.dictionary_service import DictionaryService

def main():
    app = create_app()
    with app.app_context():
        dict_service = app.injector.get(DictionaryService)
        try:
            entries = dict_service.list_entries(limit=10)
            print("Available entry IDs:")
            for entry in entries:
                print(f"  - {getattr(entry, 'id', getattr(entry, '_id', 'Unknown ID'))}")
                print(f"    Type: {type(entry)}")
                if hasattr(entry, '__dict__'):
                    print(f"    Attributes: {list(entry.__dict__.keys())}")
                break  # Just show first entry details
        except Exception as e:
            print(f"Error listing entries: {e}")

if __name__ == "__main__":
    main()
