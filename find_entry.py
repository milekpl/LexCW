#!/usr/bin/env python3
"""
Quick script to find an existing entry ID for testing.
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from app.services.dictionary_service import DictionaryService

app = create_app()
with app.app_context():
    dict_service = app.injector.get(DictionaryService)
    
    # Search for any entry
    result = dict_service.search_entries("", limit=5)
    entries, total = result if isinstance(result, tuple) else (result, len(result))
    print(f"Found {len(entries)} entries (total: {total}):")
    
    for entry in entries:
        print(f"- ID: {entry.id}")
        print(f"  Lexical unit: {entry.lexical_unit}")
        print(f"  Senses: {len(entry.senses)}")
        if entry.senses:
            for i, sense in enumerate(entry.senses):
                print(f"    Sense {i}: definition={sense.definition}, grammatical_info={sense.grammatical_info}")
        print()
